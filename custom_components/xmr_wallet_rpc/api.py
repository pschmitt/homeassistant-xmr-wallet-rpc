"""Monero Wallet RPC client."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests
from requests.auth import HTTPDigestAuth

from .const import DEFAULT_REQUEST_TIMEOUT, MAX_TRANSFERS
from .exceptions import (
    XmrWalletAuthError,
    XmrWalletConnectionError,
    XmrWalletError,
    XmrWalletRpcError,
)

_LOGGER = logging.getLogger(__name__)

_PICOMONERO = 1_000_000_000_000


def _normalize_endpoint(endpoint: str) -> str:
    """Normalize an endpoint string to a full /json_rpc URL."""
    endpoint = endpoint.strip()
    if not endpoint.startswith(("http://", "https://")):
        endpoint = f"http://{endpoint}"
    if not endpoint.endswith("/json_rpc"):
        endpoint = endpoint.rstrip("/") + "/json_rpc"
    return endpoint


@dataclass
class XmrAccountData:
    """Represents one Monero account with balance and recent transfers."""

    account_index: int
    label: str
    base_address: str
    balance: float
    unlocked_balance: float
    sub_addresses: list[dict[str, Any]] = field(default_factory=list)
    transactions: list[dict[str, Any]] = field(default_factory=list)
    last_polled_at: datetime | None = None


class XmrWalletRpcClient:
    """Client for monero-wallet-rpc with ordered-endpoint fallback."""

    def __init__(
        self,
        endpoints: list[str],
        username: str = "",
        password: str = "",
    ) -> None:
        self._endpoints = [_normalize_endpoint(ep) for ep in endpoints if ep.strip()]
        self._username = username
        self._password = password
        self._preferred_idx = 0

    def _rpc(self, method: str, params: dict | None = None) -> Any:
        """Send a JSON-RPC call, trying each endpoint in order starting from the last known good one."""
        payload = {"jsonrpc": "2.0", "id": "0", "method": method, "params": params or {}}
        auth = HTTPDigestAuth(self._username, self._password) if self._username else None

        ordered = self._endpoints[self._preferred_idx:] + self._endpoints[: self._preferred_idx]
        last_exc: Exception | None = None

        for offset, url in enumerate(ordered):
            try:
                resp = requests.post(url, json=payload, auth=auth, timeout=DEFAULT_REQUEST_TIMEOUT)
                if resp.status_code == 401:
                    raise XmrWalletAuthError(f"Authentication failed for {url}")
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    raise XmrWalletRpcError(f"RPC error from {url}: {data['error']}")
                # Remember this working endpoint for next time
                self._preferred_idx = (self._preferred_idx + offset) % len(self._endpoints)
                return data["result"]
            except (XmrWalletAuthError, XmrWalletRpcError):
                raise
            except Exception as exc:
                _LOGGER.debug("Endpoint %s failed: %s", url, exc)
                last_exc = exc

        raise XmrWalletConnectionError(
            f"All {len(self._endpoints)} endpoint(s) failed. Last error: {last_exc}"
        ) from last_exc

    def fetch_data(self) -> dict[int, XmrAccountData]:
        """Fetch all accounts, their balances, sub-addresses, and recent transfers."""
        try:
            result = self._rpc("get_accounts")
        except (XmrWalletAuthError, XmrWalletRpcError):
            raise
        except Exception as exc:
            raise XmrWalletConnectionError(str(exc)) from exc

        data: dict[int, XmrAccountData] = {}
        for acct in result.get("subaddress_accounts", []):
            idx = acct["account_index"]
            balance = acct.get("balance", 0) / _PICOMONERO
            unlocked = acct.get("unlocked_balance", 0) / _PICOMONERO

            sub_addresses = self._fetch_sub_addresses(idx)
            transactions = self._fetch_transfers(idx)

            data[idx] = XmrAccountData(
                account_index=idx,
                label=acct.get("label", ""),
                base_address=acct.get("base_address", ""),
                balance=balance,
                unlocked_balance=unlocked,
                sub_addresses=sub_addresses,
                transactions=transactions,
            )

        return data

    def _fetch_sub_addresses(self, account_index: int) -> list[dict[str, Any]]:
        try:
            result = self._rpc("get_address", {"account_index": account_index})
            return [
                {
                    "address_index": a["address_index"],
                    "address": a["address"],
                    "label": a.get("label", ""),
                    "used": a.get("used", False),
                }
                for a in result.get("addresses", [])
            ]
        except XmrWalletError:
            raise
        except Exception as exc:
            _LOGGER.warning("Failed to fetch sub-addresses for account %d: %s", account_index, exc)
            return []

    def _fetch_transfers(self, account_index: int) -> list[dict[str, Any]]:
        try:
            result = self._rpc(
                "get_transfers",
                {
                    "in": True,
                    "out": True,
                    "pending": True,
                    "pool": True,
                    "account_index": account_index,
                },
            )
            transfers: list[dict[str, Any]] = []
            for tx_type in ("in", "out", "pending", "pool"):
                for tx in result.get(tx_type, []):
                    transfers.append(
                        {
                            "type": tx_type,
                            "txid": tx.get("txid", ""),
                            "amount": tx.get("amount", 0) / _PICOMONERO,
                            "fee": tx.get("fee", 0) / _PICOMONERO,
                            "height": tx.get("height", 0),
                            "timestamp": tx.get("timestamp", 0),
                            "confirmations": tx.get("confirmations", 0),
                            "address": tx.get("address", ""),
                            "note": tx.get("note", ""),
                            "payment_id": tx.get("payment_id", ""),
                            "subaddr_index": tx.get("subaddr_index", {}),
                        }
                    )
            transfers.sort(key=lambda t: t["timestamp"], reverse=True)
            return transfers[:MAX_TRANSFERS]
        except XmrWalletError:
            raise
        except Exception as exc:
            _LOGGER.warning("Failed to fetch transfers for account %d: %s", account_index, exc)
            return []

    def validate(self) -> dict[int, XmrAccountData]:
        """Validate connection; raises XmrWalletConnectionError or XmrWalletAuthError on failure."""
        return self.fetch_data()
