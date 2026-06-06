"""Base entity for Monero Wallet RPC."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XmrCoordinator


class XmrEntity(CoordinatorEntity[XmrCoordinator]):
    """Base entity for all XMR Wallet RPC sensors."""

    _attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.config_entry
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Monero Project",
            model="monero-wallet-rpc",
        )
