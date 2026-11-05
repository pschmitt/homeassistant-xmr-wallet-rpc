<p align="center">
  <img src="logo.png" width="128" alt="Monero Wallet RPC integration logo">
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=pschmitt&amp;repository=homeassistant-xmr-wallet-rpc&amp;category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open this integration in Home Assistant Marketplace"></a>
</p>

<h1 align="center">Monero Wallet RPC for Home Assistant</h1>

<p align="center">Expose Monero wallet balances and recent transfers as Home Assistant sensors.</p>

## Features

- **Account balances:** Create one sensor per wallet account, including locked and unlocked balances and recent transfers.
- **Ordered failover:** Try multiple RPC endpoints in order when the primary wallet endpoint is unreachable. See [Wallet setup](docs/wallet-setup.md).
- **Cached data:** Retain the last known balances across restarts and temporary failures.
- **UI configuration:** Adjust endpoints, credentials and polling interval, with reauthentication and repair flows.

## Install

Use the Marketplace badge above on Home Assistant 2026.11 or later to add this
repository as a custom integration. On older versions, add it as a HACS
custom repository of type **Integration**. Install and restart Home Assistant.
The badge does not imply a public catalog listing. For manual installation,
copy `custom_components/xmr_wallet_rpc/` into Home Assistant's
`custom_components/` directory and restart.

## Quick start

1. Start a `monero-wallet-rpc` instance reachable from Home Assistant.
2. Add **Monero Wallet RPC** under **Settings → Devices & services → Add integration**.
3. Enter the RPC endpoint (such as `wallet.example.com:18084`) and optional login.
4. Inspect the balance sensor for your wallet accounts.

## Documentation

| Topic | Description |
|-------|-------------|
| [Wallet setup](docs/wallet-setup.md) | RPC endpoints, sensor attributes, reconfiguration and repairs |

## License

[GPL-3.0-or-later](LICENSE).
