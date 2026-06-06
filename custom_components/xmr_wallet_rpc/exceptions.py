"""Exceptions for the Monero Wallet RPC integration."""

from __future__ import annotations


class XmrWalletError(Exception):
    """Base exception for XMR Wallet RPC errors."""


class XmrWalletConnectionError(XmrWalletError):
    """Raised when the wallet RPC cannot be reached."""


class XmrWalletAuthError(XmrWalletError):
    """Raised when authentication to the wallet RPC fails."""


class XmrWalletRpcError(XmrWalletError):
    """Raised when the wallet RPC returns a JSON-RPC error."""
