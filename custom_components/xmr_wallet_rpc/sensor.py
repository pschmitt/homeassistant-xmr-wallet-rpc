"""Sensor platform for Monero Wallet RPC account balances."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import XmrAccountData
from .const import DOMAIN
from .coordinator import XmrCoordinator
from .entity import XmrEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up XMR balance sensors from a config entry."""
    coordinator: XmrCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    known_accounts: set[int] = set()

    @callback
    def _add_missing() -> None:
        new: list[SensorEntity] = []
        for account_index, account in coordinator.data.items():
            if account_index in known_accounts:
                continue
            known_accounts.add(account_index)
            new.append(XmrBalanceSensor(coordinator=coordinator, account=account))
        if new:
            async_add_entities(new)

    _add_missing()
    config_entry.async_on_unload(coordinator.async_add_listener(_add_missing))


class XmrBalanceSensor(XmrEntity, SensorEntity):
    """Sensor representing the balance of one Monero account."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "XMR"
    _attr_suggested_display_precision = 6
    _attr_icon = "cib:monero"
    # Exclude large list attributes from the recorder to avoid DB bloat
    _unrecorded_attributes = frozenset({"transfers", "sub_addresses"})

    def __init__(self, coordinator: XmrCoordinator, account: XmrAccountData) -> None:
        super().__init__(coordinator)
        self._account_index = account.account_index
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}:{account.account_index}:balance"
        if account.account_index == 0:
            self._attr_translation_key = "balance"
        else:
            self._attr_name = f"Account {account.account_index} Balance"

    @property
    def _account(self) -> XmrAccountData | None:
        return self.coordinator.data.get(self._account_index)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._account is not None

    @property
    def native_value(self) -> float | None:
        account = self._account
        return account.balance if account else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        account = self._account
        if account is None:
            return {}
        return {
            "unlocked_balance": account.unlocked_balance,
            "locked_balance": round(account.balance - account.unlocked_balance, 12),
            "account_index": account.account_index,
            "label": account.label,
            "base_address": account.base_address,
            "sub_addresses": account.sub_addresses,
            "transfers": account.transfers,
        }
