"""Constants for the Monero Wallet RPC integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "xmr_wallet_rpc"
PLATFORMS: list[Platform] = [Platform.EVENT, Platform.SENSOR]

CONF_ENDPOINTS = "endpoints"

DEFAULT_SCAN_INTERVAL = 3600
MIN_SCAN_INTERVAL = 60
DEFAULT_REQUEST_TIMEOUT = 10
MAX_TRANSFERS = 50

REPAIR_CANNOT_CONNECT = "cannot_connect"
