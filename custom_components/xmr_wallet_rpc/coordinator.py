"""Data update coordinator for Monero Wallet RPC."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import XmrAccountData, XmrWalletRpcClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, REPAIR_CANNOT_CONNECT
from .exceptions import XmrWalletAuthError, XmrWalletConnectionError, XmrWalletRpcError

_LOGGER = logging.getLogger(__name__)


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

    async def _async_update_data(self) -> dict[int, XmrAccountData]:
        issue_id = f"{REPAIR_CANNOT_CONNECT}_{self.config_entry.entry_id}"
        wallet_name = self.config_entry.title

        try:
            data = await self.hass.async_add_executor_job(self.client.fetch_data)
        except XmrWalletAuthError as err:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.ERROR,
                translation_key=REPAIR_CANNOT_CONNECT,
                translation_placeholders={"wallet_name": wallet_name},
            )
            raise UpdateFailed(f"Authentication failed for {wallet_name}: {err}") from err
        except (XmrWalletConnectionError, XmrWalletRpcError) as err:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=REPAIR_CANNOT_CONNECT,
                translation_placeholders={"wallet_name": wallet_name},
            )
            raise UpdateFailed(f"Connection error for {wallet_name}: {err}") from err

        ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        return data
