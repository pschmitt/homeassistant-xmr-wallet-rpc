# Wallet setup

Run `monero-wallet-rpc` with a wallet accessible to Home Assistant. For
example, configure a wallet file, RPC port, optional RPC login and daemon
address according to the
[Monero wallet RPC documentation](https://www.getmonero.org/resources/developer-guides/wallet-rpc.html).

In Home Assistant, add **Monero Wallet RPC** and enter one or more endpoints,
one per line (for example `wallet.example.com:18084`). The HTTP or HTTPS prefix
and `/json_rpc` suffix are added automatically. Endpoints are tried in order;
when the first is unreachable, the next is used. Enter the optional RPC
username and password and a display name (default `XMR`).

## Sensors

Each configured wallet is a Home Assistant device. Its balance sensor reports
XMR total balance and attributes for `unlocked_balance`, `locked_balance`,
`base_address`, `sub_addresses`, `transfers`, `last_polled_at`, `last_error`
and `stale`. Multi-account wallets get a separate
`sensor.<name>_account_N_balance` for each account index. Cached balances
survive restarts and transient RPC failures.

Each transfer in the `transfers` attribute has a `type` (`in`, `out`,
`pending` or `pool`), `txid`, XMR `amount`, `fee`, Unix `timestamp`,
`confirmations`, counterparty `address` and optional `note`.

## Reconfiguration and repair

Use **Settings → Devices & services → Monero Wallet RPC → Configure** to update
endpoints, credentials, wallet name or polling interval. When the RPC is
unreachable, the integration retries reloads before raising a repair issue
for persistent failure. Authentication failures trigger reauthentication.
