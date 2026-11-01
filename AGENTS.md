# Agent instructions

## Project

This Home Assistant integration connects to `monero-wallet-rpc` and exposes wallet balances and transfer history as sensor entities. It supports multiple RPC endpoints with ordered failover.

## Working in this repository

- Read `README.md` before changing RPC configuration, failover, polling, or repair behavior.
- Keep wallet credentials in Home Assistant config entries and out of source, logs, and fixtures.
- Before changing CI, check [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) for reusable components and preserve this repository's existing checks.

## Validation

- Run `uvx ruff check .` and `uvx ruff format --check .` for Python changes.
- CI runs Hassfest and the shared Ruff checks; it currently has no test job.
