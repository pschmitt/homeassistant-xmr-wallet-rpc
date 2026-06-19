"""Event platform for Monero Wallet RPC — fires on new transfers."""

from __future__ import annotations

import logging

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import XmrCoordinator
from .entity import XmrEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Monero Wallet RPC last-transaction event entity."""
    coordinator: XmrCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities([XmrLastTransactionEvent(coordinator)])


class XmrLastTransactionEvent(XmrEntity, EventEntity):
    """Event entity that fires when a new Monero transfer is detected.

    Watches all sub-accounts in the wallet and fires on the most recently
    timestamped transfer across all of them.
    """

    _attr_event_types = ["transaction"]
    _attr_name = "Last transaction"
    _attr_icon = "mdi:bank-transfer"

    def __init__(self, coordinator: XmrCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}:last_transaction"
        self._last_txid: str | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data
        if not data:
            super()._handle_coordinator_update()
            return

        latest = _latest_transfer(data)
        if latest is None:
            super()._handle_coordinator_update()
            return

        txid = latest.get("txid")

        if self._last_txid is None:
            self._last_txid = txid
        elif txid is not None and txid != self._last_txid:
            self._last_txid = txid
            self._trigger_event(
                "transaction",
                {
                    "txid": txid,
                    "type": latest.get("type"),
                    "amount": latest.get("amount"),
                    "fee": latest.get("fee"),
                    "height": latest.get("height"),
                    "timestamp": latest.get("timestamp"),
                    "confirmations": latest.get("confirmations"),
                    "address": latest.get("address"),
                    "note": latest.get("note"),
                    "payment_id": latest.get("payment_id"),
                },
            )
            return  # _trigger_event already calls async_write_ha_state

        super()._handle_coordinator_update()


def _latest_transfer(data: dict) -> dict | None:
    """Return the most recently timestamped transfer across all sub-accounts."""
    best: dict | None = None
    best_ts = -1
    for account in data.values():
        for tx in (account.transactions or []):
            ts = tx.get("timestamp") or 0
            if ts > best_ts:
                best_ts = ts
                best = tx
    return best
