"""Data update coordinator for Monero Wallet RPC."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import XmrAccountData, XmrWalletRpcClient
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_RELOAD_RETRIES,
    RELOAD_RETRY_DELAY_SECONDS,
    REPAIR_CANNOT_CONNECT,
    STORAGE_VERSION,
)
from .exceptions import XmrWalletAuthError, XmrWalletConnectionError, XmrWalletRpcError

_LOGGER = logging.getLogger(__name__)
_RETRY_STATE_KEY = "__retry_state__"


class XmrCoordinator(DataUpdateCoordinator[dict[int, XmrAccountData]]):
    """Coordinate periodic fetches for one Monero wallet RPC connection."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: XmrWalletRpcClient,
        config_entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(
                seconds=config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        self.last_refresh: datetime | None = None
        self.last_error: str = ""
        self._cached: dict[int, XmrAccountData] = {}
        self._cancel_retry_reload: Any | None = None
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{config_entry.entry_id}.cache"
        )

    async def async_load_cache(self) -> None:
        """Load cached balances and seed coordinator data before first refresh."""
        stored = await self._store.async_load() or {}
        accounts = stored.get("accounts")
        if isinstance(accounts, dict):
            for account_index, raw in accounts.items():
                if not isinstance(raw, dict):
                    continue
                account = _account_from_stored(raw)
                if account is None:
                    continue
                self._cached[account.account_index] = account

        self.last_refresh = _parse_iso(stored.get("last_polled_at"))

        if self._cached:
            _LOGGER.debug(
                "Hydrated %d cached Monero account(s) for entry %s",
                len(self._cached),
                self.config_entry.entry_id,
            )
            self.async_set_updated_data(dict(self._cached))

    async def _save_cache(self) -> None:
        """Persist the latest successful account snapshot."""
        await self._store.async_save(
            {
                "last_polled_at": self.last_refresh.isoformat()
                if self.last_refresh
                else None,
                "accounts": {
                    str(account_index): _account_to_stored(account)
                    for account_index, account in self._cached.items()
                },
            }
        )

    def cached_account(self, account_index: int) -> XmrAccountData | None:
        """Return the last cached snapshot for an account."""
        return self._cached.get(account_index)

    @property
    def _retry_state(self) -> dict[str, Any]:
        """Shared retry state that survives integration reloads."""
        return self.hass.data.setdefault(DOMAIN, {}).setdefault(_RETRY_STATE_KEY, {}).setdefault(
            self.config_entry.entry_id,
            {"consecutive_failures": 0, "reload_pending": False},
        )

    def _reset_retry_state(self) -> None:
        """Clear transient connection failure state after a successful refresh."""
        self._retry_state["consecutive_failures"] = 0
        self._retry_state["reload_pending"] = False
        if self._cancel_retry_reload is not None:
            self._cancel_retry_reload()
            self._cancel_retry_reload = None

    def _schedule_reload_retry(self) -> None:
        """Schedule a delayed integration reload if one is not already pending."""
        if self._retry_state["reload_pending"]:
            return

        self._retry_state["reload_pending"] = True

        async def _reload_entry(_now: datetime) -> None:
            self._retry_state["reload_pending"] = False
            self._cancel_retry_reload = None
            _LOGGER.debug(
                "Retrying Monero Wallet RPC entry %s via reload after connection failure",
                self.config_entry.entry_id,
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

        self._cancel_retry_reload = async_call_later(
            self.hass, RELOAD_RETRY_DELAY_SECONDS, _reload_entry
        )
        self.config_entry.async_on_unload(self._cancel_retry_reload)

    async def _async_update_data(self) -> dict[int, XmrAccountData]:
        issue_id = f"{REPAIR_CANNOT_CONNECT}_{self.config_entry.entry_id}"
        wallet_name = self.config_entry.title

        try:
            data = await self.hass.async_add_executor_job(self.client.fetch_data)
        except XmrWalletAuthError as err:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            self.last_error = "auth"
            _LOGGER.warning(
                "Authentication failed for %s; keeping cached balances: %s",
                wallet_name,
                err,
            )
            self.config_entry.async_start_reauth(self.hass)
            return self._cached_snapshot()
        except (XmrWalletConnectionError, XmrWalletRpcError) as err:
            self.last_error = "cannot_connect"
            retry_state = self._retry_state
            retry_state["consecutive_failures"] += 1
            failure_count = retry_state["consecutive_failures"]

            if failure_count <= MAX_RELOAD_RETRIES:
                _LOGGER.warning(
                    "Connection error for %s; keeping cached balances and scheduling reload "
                    "retry %d/%d in %ds: %s",
                    wallet_name,
                    failure_count,
                    MAX_RELOAD_RETRIES,
                    RELOAD_RETRY_DELAY_SECONDS,
                    err,
                )
                self._schedule_reload_retry()
                return self._cached_snapshot()

            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=REPAIR_CANNOT_CONNECT,
                translation_placeholders={"wallet_name": wallet_name},
            )
            _LOGGER.warning(
                "Connection error for %s after %d reload retries; raising repair and "
                "keeping cached balances: %s",
                wallet_name,
                MAX_RELOAD_RETRIES,
                err,
            )
            return self._cached_snapshot()

        ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        self.last_error = ""
        self._reset_retry_state()
        self.last_refresh = dt_util.utcnow()
        for account in data.values():
            account.last_polled_at = self.last_refresh

        self._cached = dict(data)
        await self._save_cache()
        return dict(self._cached)

    def _cached_snapshot(self) -> dict[int, XmrAccountData]:
        """Return the best available snapshot without raising."""
        return dict(self._cached)


def _account_from_stored(data: dict[str, Any]) -> XmrAccountData | None:
    """Hydrate a cached account snapshot from storage."""
    try:
        return XmrAccountData(
            account_index=int(data["account_index"]),
            label=str(data.get("label", "")),
            base_address=str(data.get("base_address", "")),
            balance=float(data["balance"]),
            unlocked_balance=float(data["unlocked_balance"]),
            sub_addresses=data.get("sub_addresses")
            if isinstance(data.get("sub_addresses"), list)
            else [],
            transactions=data.get("transactions")
            if isinstance(data.get("transactions"), list)
            else [],
            last_polled_at=_parse_iso(data.get("last_polled_at")),
        )
    except (KeyError, TypeError, ValueError):
        _LOGGER.debug("Skipping malformed Monero cache entry: %r", data)
        return None


def _account_to_stored(account: XmrAccountData) -> dict[str, Any]:
    """Serialize an account snapshot to storage."""
    return {
        "account_index": account.account_index,
        "label": account.label,
        "base_address": account.base_address,
        "balance": account.balance,
        "unlocked_balance": account.unlocked_balance,
        "sub_addresses": account.sub_addresses,
        "transactions": account.transactions,
        "last_polled_at": account.last_polled_at.isoformat()
        if account.last_polled_at
        else None,
    }


def _parse_iso(value: Any) -> datetime | None:
    """Parse an ISO timestamp from storage."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
