# Monero Wallet RPC for Home Assistant

`xmr_wallet_rpc` is a Home Assistant custom integration that connects to your
[monero-wallet-rpc](https://www.getmonero.org/resources/developer-guides/wallet-rpc.html)
daemon and exposes wallet balances and transfer history as sensor entities.

## Features

- One Home Assistant **device** per wallet configuration
- One **balance sensor** per Monero account (account index), with state = total balance in XMR
- Rich sensor attributes: unlocked balance, locked balance, sub-addresses, recent transfers
- **Multiple RPC endpoints** with automatic ordered failover — if the first endpoint is
  unreachable, the next one is tried automatically
- Cached balances survive Home Assistant restarts and transient wallet/RPC failures
- Fully configurable via the HA UI (no YAML needed)
- Options flow to tune the poll interval
- Reconfigure flow to update endpoints, credentials, or wallet name without deleting the entry
- Retries integration reloads several times before raising a **repair issue** for unreachable RPC endpoints

## Requirements

A running `monero-wallet-rpc` instance reachable from your Home Assistant server:

```sh
monero-wallet-rpc \
  --wallet-file /path/to/wallet \
  --rpc-bind-port 18084 \
  --rpc-login user:password \   # optional; omit if no auth
  --daemon-address 127.0.0.1:18081
```

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pschmitt&repository=homeassistant-xmr-wallet-rpc&category=integration)

1. Click the badge above — or open HACS → Integrations → ⋮ → Custom repositories and add
   `https://github.com/pschmitt/homeassistant-xmr-wallet-rpc` as type **Integration**.
2. Install **Monero Wallet RPC**.
3. Restart Home Assistant.

### Manual

Copy the `custom_components/xmr_wallet_rpc/` directory from this repository into your Home
Assistant `custom_components/` folder, then restart.

## Configuration

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **Monero Wallet RPC**.
3. Fill in:
   - **RPC endpoint(s)** — one per line, e.g. `192.168.1.100:18084`. HTTP/HTTPS prefix and the
     `/json_rpc` path suffix are added automatically. Enter multiple endpoints for failover.
   - **Username** — optional; the user part of `--rpc-login`.
   - **Password** — optional; the password part of `--rpc-login`.
   - **Wallet name** — display name for the HA device (default: `XMR`).

## Sensors

| Sensor | State | Key attributes |
|--------|-------|----------------|
| `sensor.<name>_balance` | Total XMR balance | `unlocked_balance`, `locked_balance`, `base_address`, `sub_addresses`, `transfers`, `last_polled_at`, `last_error`, `stale` |
| `sensor.<name>_account_N_balance` *(multi-account)* | Balance for account N | same as above |

Transfer entries in the `transfers` attribute:

| Field | Description |
|-------|-------------|
| `type` | `in`, `out`, `pending`, or `pool` |
| `txid` | Transaction ID |
| `amount` | XMR amount |
| `fee` | Miner fee in XMR |
| `timestamp` | Unix timestamp |
| `confirmations` | Block confirmations |
| `address` | Counterparty address |
| `note` | Optional note |

## Reconfiguration & repair

To change endpoints, credentials, or wallet name: **Settings → Devices & services →
Monero Wallet RPC → Configure**.

When the wallet RPC is temporarily unreachable, the integration retries by reloading itself a few
times first. Only persistent failures raise a repair issue in HA. Authentication failures still
trigger reauthentication immediately.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
