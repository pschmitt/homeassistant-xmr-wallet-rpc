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
    timestamped transfer across all of them. New-transaction detection lives
    in the coordinator (coordinator.new_transaction), whose last-seen txid is
    persisted to disk — this entity gets recreated on every reload (e.g. the
    connection-failure retry-reload loop), so tracking the baseline in-memory
    here would silently swallow notifications for the first transaction seen
    after any such reload.
    """

    _attr_event_types = ["transaction"]
    _attr_name = "Last transaction"
    _attr_icon = "mdi:bank-transfer"

    def __init__(self, coordinator: XmrCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}:last_transaction"

    @callback
    def _handle_coordinator_update(self) -> None:
        new_transaction = self.coordinator.new_transaction
        if new_transaction is not None:
            self._trigger_event(
                "transaction",
                {
                    "txid": new_transaction.get("txid"),
                    "type": new_transaction.get("type"),
                    "amount": new_transaction.get("amount"),
                    "fee": new_transaction.get("fee"),
                    "height": new_transaction.get("height"),
                    "timestamp": new_transaction.get("timestamp"),
                    "confirmations": new_transaction.get("confirmations"),
                    "address": new_transaction.get("address"),
                    "note": new_transaction.get("note"),
                    "payment_id": new_transaction.get("payment_id"),
                },
            )
            return  # _trigger_event already calls async_write_ha_state

        super()._handle_coordinator_update()
