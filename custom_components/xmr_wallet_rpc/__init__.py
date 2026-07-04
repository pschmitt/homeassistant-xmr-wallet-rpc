"""The Monero Wallet RPC integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .api import XmrWalletRpcClient
from .const import CONF_ENDPOINTS, DOMAIN, PLATFORMS
from .coordinator import XmrCoordinator

RETRY_STATE_KEY = "__retry_state__"


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Monero Wallet RPC from a config entry."""
    runtime = hass.data.setdefault(DOMAIN, {})
    retry_state = runtime.setdefault(RETRY_STATE_KEY, {})
    entry_retry_state = retry_state.setdefault(
        config_entry.entry_id,
        {"consecutive_failures": 0, "reload_pending": False},
    )
    entry_retry_state["reload_pending"] = False

    client = XmrWalletRpcClient(
        endpoints=config_entry.data[CONF_ENDPOINTS],
        username=config_entry.data.get(CONF_USERNAME, ""),
        password=config_entry.data.get(CONF_PASSWORD, ""),
    )
    coordinator = XmrCoordinator(hass, client, config_entry)
    await coordinator.async_load_cache()
    await coordinator.async_config_entry_first_refresh()

    runtime[config_entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a Monero Wallet RPC config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
    return unload_ok


async def async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(config_entry.entry_id)
