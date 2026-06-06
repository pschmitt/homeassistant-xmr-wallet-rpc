"""Config flow for Monero Wallet RPC."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import XmrWalletRpcClient
from .const import CONF_ENDPOINTS, DEFAULT_SCAN_INTERVAL, DOMAIN, MIN_SCAN_INTERVAL
from .exceptions import XmrWalletAuthError, XmrWalletConnectionError

_LOGGER = logging.getLogger(__name__)


def _parse_endpoints(raw: str) -> list[str]:
    """Split comma-or-newline separated endpoint strings into a list."""
    return [p.strip() for p in re.split(r"[,\n]+", raw) if p.strip()]


async def _validate(hass: HomeAssistant, data: dict[str, Any]) -> None:
    client = XmrWalletRpcClient(
        endpoints=data[CONF_ENDPOINTS],
        username=data.get(CONF_USERNAME, ""),
        password=data.get(CONF_PASSWORD, ""),
    )
    await hass.async_add_executor_job(client.validate)


def _build_schema(
    defaults: dict[str, Any],
    *,
    password_required: bool = True,
    show_name: bool = True,
) -> vol.Schema:
    endpoint_default = "\n".join(defaults.get(CONF_ENDPOINTS) or [""])
    fields: dict[vol.Marker, Any] = {
        vol.Required(CONF_ENDPOINTS, default=endpoint_default): TextSelector(
            TextSelectorConfig(multiline=True)
        ),
        vol.Optional(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): TextSelector(),
    }
    if password_required:
        fields[vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, ""))] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    else:
        fields[vol.Optional(CONF_PASSWORD)] = TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    if show_name:
        fields[vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, "XMR"))] = TextSelector()
    return vol.Schema(fields)


class XmrWalletRpcConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Monero Wallet RPC."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> XmrWalletRpcOptionsFlow:
        return XmrWalletRpcOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            endpoints = _parse_endpoints(user_input[CONF_ENDPOINTS])
            if not endpoints:
                errors[CONF_ENDPOINTS] = "no_endpoints"
            else:
                data = {
                    CONF_ENDPOINTS: endpoints,
                    CONF_USERNAME: user_input.get(CONF_USERNAME, ""),
                    CONF_PASSWORD: user_input.get(CONF_PASSWORD, ""),
                }
                name = user_input.get(CONF_NAME) or "XMR"
                try:
                    await _validate(self.hass, data)
                except XmrWalletAuthError:
                    errors["base"] = "invalid_auth"
                except XmrWalletConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during XMR Wallet RPC config validation")
                    errors["base"] = "unknown"
                else:
                    await self.async_set_unique_id(f"xmr_wallet:{endpoints[0]}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=name,
                        data=data,
                        options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema({}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            endpoints = _parse_endpoints(user_input[CONF_ENDPOINTS])
            if not endpoints:
                errors[CONF_ENDPOINTS] = "no_endpoints"
            else:
                password = user_input.get(CONF_PASSWORD) or entry.data.get(CONF_PASSWORD, "")
                merged = {
                    **entry.data,
                    CONF_ENDPOINTS: endpoints,
                    CONF_USERNAME: user_input.get(CONF_USERNAME, ""),
                    CONF_PASSWORD: password,
                }
                name = user_input.get(CONF_NAME) or entry.title
                try:
                    await _validate(self.hass, merged)
                except XmrWalletAuthError:
                    errors["base"] = "invalid_auth"
                except XmrWalletConnectionError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during XMR Wallet RPC reconfigure validation")
                    errors["base"] = "unknown"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        title=name,
                        data=merged,
                    )

        defaults = {
            **entry.data,
            CONF_NAME: entry.title,
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_build_schema(defaults, password_required=False),
            errors=errors,
        )


class XmrWalletRpcOptionsFlow(OptionsFlow):
    """Handle options for Monero Wallet RPC."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            mode=NumberSelectorMode.BOX,
                            step=1,
                        )
                    )
                }
            ),
        )
