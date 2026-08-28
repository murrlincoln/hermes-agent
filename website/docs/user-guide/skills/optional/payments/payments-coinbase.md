---
title: "Coinbase — Manage Coinbase accounts, trading, and portfolios"
sidebar_label: "Coinbase"
description: "Manage Coinbase accounts, trading, and portfolios"
---

{/* This page is auto-generated from the skill's SKILL.md by website/scripts/generate-skill-docs.py. Edit the source SKILL.md, not this page. */}

# Coinbase

Manage Coinbase accounts, trading, and portfolios.

## Skill metadata

| | |
|---|---|
| Source | Optional — install with `hermes skills install official/payments/coinbase` |
| Path | `optional-skills/payments/coinbase` |
| Version | `0.2.0` |
| Author | Ethan Oroshiba (ethanoroshiba), Hermes Agent |
| License | MIT |
| Platforms | linux, macos, windows |
| Tags | `Coinbase`, `Crypto`, `Trading`, `Portfolios`, `Brokerage` |
| Related skills | [`mcp-oauth-remote-gateway`](/docs/user-guide/skills/optional/mcp/mcp-mcp-oauth-remote-gateway) |

## Reference: full SKILL.md

:::info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
:::

# Coinbase Skill

Use the hosted Coinbase MCP server (`https://agents.coinbase.com/mcp`) for brokerage: balances,
portfolios, market data, and user-approved spot / futures / equity orders. Prefer its typed
`coinbase_*` tools over terminal commands. The server handles OAuth and acts on the user's behalf;
it does not fund an account and does not replace explicit confirmation for state-changing actions.

## When to Use

- Check balances, products, fees, orders, fills, or portfolios.
- Analyze markets and (after user approval) place, preview, modify, or cancel orders.
- Convert between USDC and USD, or transfer between portfolios.
- Set up user-approved, explicitly bounded trading automations.

Do not use for: account funding (direct the user to Coinbase web/mobile), generic public prices with
no Coinbase context, onchain/DeFi activity, or external-wallet sends (the server exposes no external
withdrawal tools; `coinbase_transfer` moves funds only between Coinbase portfolios).

> Coming soon, not yet available: x402 payments for agent-consumed services. They are not exposed by
> this server yet.

## Prerequisites

Install via the catalog (`hermes mcp install coinbase`) or add directly to `config.yaml`:

```yaml
mcp_servers:
  coinbase:
    url: "https://agents.coinbase.com/mcp"
    auth: oauth
```

Reload MCP servers, complete the browser OAuth flow, and confirm the Coinbase tools are available.
During consent, select only the portfolios you intend to expose. If OAuth expires run
`hermes mcp reauth coinbase`; on a headless gateway use the `mcp-oauth-remote-gateway` skill.

Note: the remote server is gated to an explicit harness allowlist (ChatGPT, Claude, Claude Code;
Codex/others pending). If OAuth completes but no tools load, confirm Hermes is allowlisted.

## How to Run

The tools appear in Hermes as `mcp__coinbase__<tool>` (e.g. `mcp__coinbase__coinbase_balance`). Use
the live tool schemas and responses as authoritative over this reference; do not reconstruct
brokerage HTTP requests or fall back to shell commands.

## Safety model

Classify every operation before acting:

- **Read-only** (no confirmation needed): market data, balances, portfolios list/get, orders
  list/get/fills, fees, conversion quotes, order previews.
- **State-changing** (confirm first): orders create/edit/cancel/close-position, conversion execute,
  transfers, portfolio create/edit/delete.

Before a state-changing call, state and get confirmation of the *exact* action — for orders: product,
side, type, portfolio, exact `quote_size` or `base_size`, limit/stop prices, time-in-force, estimated
fees/slippage from a preview, and (for futures) liquidation risk. For conversions: currencies, amount,
quoted rate/fees, quote expiry. For transfers: currency, amount, source and destination portfolio.

Never:

- Split an order to evade product or notional limits.
- Substitute a different asset, quote currency, portfolio, side, order type, or leverage.
- Claim guaranteed execution, returns, tax treatment, or investment suitability.
- Call `orders_edit`, `orders_close_position`, or `portfolios_delete` unless the user explicitly
  requests that exact action and confirms after seeing consequences.
- Infer trade direction or amount from portfolio context.

## Quick Reference

Read-only: `products_list`, `products_get`, `products_ticker`, `products_book`, `products_candles`,
`products_best_bid_ask`, `balance`, `fees`, `portfolios_list`, `portfolios_get`, `orders_preview`,
`orders_list`, `orders_get`, `orders_fills`, `convert_quote`, `convert_get`.

State-changing (confirm first): `orders_create`, `orders_edit`, `orders_cancel`,
`orders_close_position`, `convert_execute`, `transfer`, `portfolios_create`, `portfolios_edit`,
`portfolios_delete`.

Key parameters:

- `balance`: `portfolio_id` (optional — defaults to the default portfolio), `show_zero`, `cursor`,
  `limit`. Returns an `accounts` array with `available_balance` and `hold`.
- `fees`: optional `product_type` (`SPOT` | `FUTURE` | `EQUITY`).
- `products_list`: filter with `symbol` (matches base or quote), `product_ids` (comma-separated
  string), `product_type` (`SPOT` | `FUTURE` | `EQUITY`), `cursor`, `limit`.
- `products_candles`: `granularity` is a strict enum `1m,5m,15m,30m,1h,2h,6h,1d` (no `4h`, no `1w`).
- `orders_*`/`orders_preview`: `side` is `BUY`|`SELL`; `type` is `market`|`limit`|`stop_limit`;
  `stop_direction` is `up`|`down`; `time_in_force` is `GTC`|`IOC`|`FOK`|`GTD`. `portfolio_id` is
  optional and defaults to the default portfolio.

## Order sizing and limits

- Set exactly one of `base_size` (asset amount) or `quote_size` (quote-currency spend).
- Market buy by spend amount uses `quote_size`. Stop-limit orders use `base_size` plus `stop_price`,
  `limit_price`, and `stop_direction`.
- Fee handling is asymmetric: a market buy deducts the fee from `quote_size`; a limit buy adds it on
  top. Preview and surface the net cost before confirming.
- Validate `base_increment` / `quote_increment` / min / max sizes from `products_get` before sizing.
- Per-order notional is capped (currently **15,000 USD equivalent**) by the server schema.
- `client_order_id` is your idempotency key (may be auto-generated if omitted). Reuse the same ID only
  when retrying the identical request after an uncertain response — never mint a new ID to retry.

## Procedure

1. Select the correct portfolio and inspect balances or market data. Resolve the product and funding
   currency: prefer the user's stated quote currency, else a USDC pair when both USD and USDC are
   available. Verify the exact product exists (`products_get`) rather than assuming a product ID.
2. For a trade, validate increments/min/max and the notional cap, then preview
   (`orders_preview`) — especially for market, limit, stop-limit, futures, large, or unfamiliar orders.
   Preview is not execution; say so.
3. State and obtain confirmation of the complete action (see Safety model). A prior strategy or general
   instruction is not authorization for a later trade.
4. Submit the confirmed call once with a stable `client_order_id`. Report the returned status; do not
   automatically follow up. If the outcome is unclear, query `orders_get` with the same `client_order_id`
   before retrying.
5. For conversions, quote first, show rate/fees, confirm, then execute only the matching `from`/`to`/
   `quote_id` (quotes expire — obtain a fresh quote immediately before execution).
6. Distinguish order status (submitted/open, partially filled, filled, rejected, cancelled). Never
   describe an order as filled unless its status or a follow-up lookup confirms it.

## Automations

Every trading automation must declare one authorization mode:

- **Monitor only** — read data and notify on a condition; never place an order.
- **Preview and ask** — evaluate, generate a preview, and ask before executing.
- **Pre-authorized execution** — execute within exact product, portfolio, cadence, sizing, and spend
  limits approved when the schedule was created.

Default to monitor-only if a mode is omitted; never infer pre-authorized execution. For scheduled work,
define per-run (and where relevant monthly) caps, cadence/timezone, failure behavior, and stop
conditions. Never exceed approved caps to "catch up" a missed run, and never bunch missed orders into
the next run. Subjective triggers (news, "good earnings") require an objective rule and explicit
executor authorization before any auto-execution.

## Pitfalls

- **Portfolio isolation:** visibility and authority are limited to portfolios authorized during OAuth.
  Never claim an unauthorized portfolio is empty or nonexistent.
- **External sends:** there is no withdrawal tool. `coinbase_transfer` is between-portfolios only.
- **Conversions are stablecoin/fiat only** (USDC/USD). To accumulate BTC/ETH etc. use a spot order.
- **Granularity / enums:** `products_candles` rejects `4h`/`1w`; `side`/`type`/`stop_direction` enums are
  case-sensitive (uppercase side, lowercase `stop_limit`).
- **Retry discipline:** after an uncertain money-moving result, query by order/quote ID; do not retry
  with a new idempotency key.
- **Error handling:** 401 → reconnect (`hermes mcp reauth coinbase`); permission denied → verify the
  portfolio is authorized, don't switch silently; insufficient funds → check *available* (not total)
  balance and the quote currency; invalid product/increments → refresh product metadata and show the
  constraints; equities/derivatives unavailable → don't promise activation.

## Verification

Confirm `coinbase_balance` (or `coinbase_portfolios_list`) returns the expected balances for the
authorized portfolio(s). A successful typed response confirms the MCP connection, OAuth authorization,
and the brokerage read path.

## Disclosure

Provide a concise risk reminder for trades and an enhanced warning for derivatives/leverage. Trading can
result in substantial loss; derivatives and leverage add liquidation risk. Output is operational
assistance, not individualized investment, legal, or tax advice — the user authorizes and remains
responsible for account activity.
