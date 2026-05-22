---
name: x402
description: "x402 payments: probe URLs, pay with USDC, manage agent wallet."
version: 1.0.0
author: Lincoln Murr (@lincolnmurr)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [x402, payments, USDC, Base, Ethereum, agentic, micropayments, stablecoin, HTTP402]
    category: blockchain
    related_skills: [evm]
    requires_toolsets: [terminal]
---

# x402 Payment Skill

Make HTTP-native payments to any x402-protected resource using the open x402
standard (Linux Foundation). Probe payment requirements, sign USDC
transferWithAuthorization payloads, settle via a facilitator, and manage a
local agent wallet — all with zero external Python dependencies.

Supports the `exact` scheme on EVM networks (Base, Ethereum, Polygon, Arbitrum,
Optimism). The Coinbase public facilitator (`https://x402.org/facilitator`) is
used by default; override with `X402_FACILITATOR_URL`.

---

## When to Use
- User wants to pay for a paywalled API endpoint that returns HTTP 402
- User wants to probe what an x402-protected URL costs before paying
- User wants to inspect the `PAYMENT-REQUIRED` header from a resource server
- User needs a fresh EVM wallet for an AI agent (key generation, address only)
- User wants to check the USDC balance of an agent wallet on Base
- User wants to verify or settle a payment directly against the facilitator
- User is integrating x402 into a project and needs to test end-to-end flow

---

## Prerequisites

Python 3.8+ standard library only. No pip installs required.

**Wallet key** — the agent needs a private key to sign payments:
- Set `X402_PRIVATE_KEY` in the environment (or `~/.hermes/.env`) to a
  32-byte hex private key (0x-prefixed or raw 64-hex-char).
- Generate a new key: `python3 $SCRIPT wallet new`

**Facilitator** — default `https://x402.org/facilitator` (Coinbase public).
Override: `export X402_FACILITATOR_URL=https://your-facilitator.example.com`

**RPC** — default public Base RPC (`https://mainnet.base.org`).
Override: `export X402_RPC_URL=https://your-rpc.example.com`

Helper script path: `~/.hermes/skills/blockchain/x402/scripts/x402_client.py`

---

## Quick Reference

```
SCRIPT=~/.hermes/skills/blockchain/x402/scripts/x402_client.py

# Wallet management
python3 $SCRIPT wallet new                        # Generate new keypair
python3 $SCRIPT wallet address                    # Show address for current key
python3 $SCRIPT wallet balance                    # USDC balance on Base

# Probe a resource (no payment sent)
python3 $SCRIPT probe https://api.example.com/premium

# Pay a resource (full flow: probe → sign → settle)
python3 $SCRIPT pay https://api.example.com/premium

# Verify a payment payload against the facilitator (no settlement)
python3 $SCRIPT verify https://api.example.com/premium

# Inspect raw 402 response headers
python3 $SCRIPT inspect https://api.example.com/premium
```

---

## Procedure

### 0. Setup Check
```bash
python3 --version   # 3.8+ required
python3 ~/.hermes/skills/blockchain/x402/scripts/x402_client.py wallet new
# Copy the private_key value and export it:
export X402_PRIVATE_KEY=0x<your_key_here>
python3 ~/.hermes/skills/blockchain/x402/scripts/x402_client.py wallet address
```

### 1. Generate an Agent Wallet
Produces a secp256k1 keypair using Python stdlib only. The private key is
printed once — save it immediately.
```bash
python3 $SCRIPT wallet new
```
Output:
```json
{
  "private_key": "0x...",
  "address": "0x..."
}
```
Store the private key in `~/.hermes/.env` as `X402_PRIVATE_KEY=0x...`.

### 2. Fund the Wallet
Send USDC on Base to the address printed by `wallet address`. Minimum balance
should exceed the `amount` in the `PaymentRequirements` for the resource you
want to access plus a small buffer for facilitator overhead.

### 3. Probe a Resource (No Payment)
Sends a plain GET request without a payment header. If the server returns 402,
parses and decodes the `PAYMENT-REQUIRED` header.
```bash
python3 $SCRIPT probe https://api.example.com/premium
```
Returns the full `PaymentRequired` JSON including `amount`, `asset`, `payTo`,
`network`, and `maxTimeoutSeconds`.

### 4. Pay a Resource (Full Flow)
Probes for requirements, builds an EIP-3009 `TransferWithAuthorization`
payload, signs it with the local key, and POSTs to the facilitator `/settle`
endpoint. On success, re-fetches the resource with the `PAYMENT-SIGNATURE`
header and prints the response body.
```bash
python3 $SCRIPT pay https://api.example.com/premium
```

### 5. Verify Without Settling
Builds and signs a payment payload (identical to `pay`), then POSTs to the
facilitator `/verify` endpoint instead of `/settle`. Useful for testing key
setup and balance sufficiency before committing funds.
```bash
python3 $SCRIPT verify https://api.example.com/premium
```

### 6. Check Balance
Calls `balanceOf` on the USDC contract on Base for the configured wallet.
```bash
python3 $SCRIPT wallet balance
```
Also accepts `--chain` for Ethereum (`ethereum`), Polygon (`polygon`),
Arbitrum (`arbitrum`), or Optimism (`optimism`).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `X402_PRIVATE_KEY` | (required for pay/verify) | 32-byte hex private key |
| `X402_FACILITATOR_URL` | `https://x402.org/facilitator` | Facilitator base URL |
| `X402_RPC_URL` | `https://mainnet.base.org` | EVM JSON-RPC endpoint |

---

## Supported Networks

| CAIP-2 ID | Name | USDC Contract |
|---|---|---|
| `eip155:8453` | Base (default) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| `eip155:1` | Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| `eip155:137` | Polygon | `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174` |
| `eip155:42161` | Arbitrum One | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| `eip155:10` | Optimism | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |

---

## Pitfalls
- `wallet new` prints the private key once; if lost, the key is unrecoverable.
- USDC uses 6 decimals. An `amount` of `"1000000"` in PaymentRequirements
  equals $1.00 USDC — not $1,000,000.
- The `maxTimeoutSeconds` field limits the `validBefore` window. The payment
  payload will be rejected by the facilitator if more than that many seconds
  elapse between signing and settlement.
- `X402_PRIVATE_KEY` must be set for `pay` and `verify`. `probe`, `inspect`,
  and `wallet balance` work without it.
- Public facilitator rate limits apply. For production use, run your own
  facilitator or contact Coinbase for elevated limits.
- The pure-Python secp256k1 implementation is suitable for testing; for
  production key management use an HSM or CDP MPC Wallet.

---

## Verification
```bash
# Should print address derived from X402_PRIVATE_KEY
python3 ~/.hermes/skills/blockchain/x402/scripts/x402_client.py wallet address

# Should return PaymentRequired JSON for a live x402 resource
python3 ~/.hermes/skills/blockchain/x402/scripts/x402_client.py probe https://x402.org/demo
```
