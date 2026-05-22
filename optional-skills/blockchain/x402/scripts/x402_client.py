#!/usr/bin/env python3
"""
x402_client.py — x402 payment protocol CLI for the Hermes Agent project.
Zero external dependencies. Uses stdlib only: urllib, json, argparse, os, sys,
secrets, hashlib, struct, typing.

Implements the x402 v2 "exact" scheme on EVM networks (EIP-3009
TransferWithAuthorization). Wallet key generation uses a pure-Python
secp256k1 implementation (suitable for development/testing).

Environment variables:
  X402_PRIVATE_KEY      32-byte hex private key (0x-prefixed or raw 64 hex chars)
  X402_FACILITATOR_URL  Facilitator base URL (default: https://x402.org/facilitator)
  X402_RPC_URL          EVM JSON-RPC URL (default: https://mainnet.base.org)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Network registry
# ---------------------------------------------------------------------------

NETWORKS: Dict[str, Dict[str, Any]] = {
    "eip155:8453": {
        "name": "Base",
        "rpc": "https://mainnet.base.org",
        "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "usdc_name": "USD Coin",
        "usdc_version": "2",
        "chain_id": 8453,
    },
    "eip155:1": {
        "name": "Ethereum",
        "rpc": "https://ethereum-rpc.publicnode.com",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "usdc_name": "USD Coin",
        "usdc_version": "2",
        "chain_id": 1,
    },
    "eip155:137": {
        "name": "Polygon",
        "rpc": "https://polygon-rpc.com",
        "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "usdc_name": "USD Coin (PoS)",
        "usdc_version": "1",
        "chain_id": 137,
    },
    "eip155:42161": {
        "name": "Arbitrum One",
        "rpc": "https://arb1.arbitrum.io/rpc",
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "usdc_name": "USD Coin",
        "usdc_version": "2",
        "chain_id": 42161,
    },
    "eip155:10": {
        "name": "Optimism",
        "rpc": "https://mainnet.optimism.io",
        "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "usdc_name": "USD Coin",
        "usdc_version": "2",
        "chain_id": 10,
    },
}

DEFAULT_NETWORK = "eip155:8453"
DEFAULT_FACILITATOR = "https://x402.org/facilitator"

# ---------------------------------------------------------------------------
# Pure-Python Keccak-256 (Ethereum's hash — NOT SHA3-256)
# Identical implementation to evm_client.py for consistency.
# ---------------------------------------------------------------------------

_KECCAK_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_KECCAK_ROT = [
    [0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56], [27, 20, 39, 8, 14],
]


def _rot64(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF


def keccak256(data: bytes) -> bytes:
    """Pure-Python Keccak-256 (Ethereum's hash, not SHA3-256)."""
    rate = 136
    msg = bytearray(data)
    msg.append(0x01)
    while len(msg) % rate != 0:
        msg.append(0x00)
    msg[-1] |= 0x80
    state = [0] * 25
    for block_start in range(0, len(msg), rate):
        block = msg[block_start:block_start + rate]
        for i in range(rate // 8):
            state[i] ^= int.from_bytes(block[i * 8:(i + 1) * 8], "little")
        for rnd in range(24):
            C = [state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20] for x in range(5)]
            D = [C[(x - 1) % 5] ^ _rot64(C[(x + 1) % 5], 1) for x in range(5)]
            state = [state[i] ^ D[i % 5] for i in range(25)]
            B = [0] * 25
            for x in range(5):
                for y in range(5):
                    B[y + 5 * ((2 * x + 3 * y) % 5)] = _rot64(state[x + 5 * y], _KECCAK_ROT[x][y])
            state = [B[i] ^ ((~B[(i // 5) * 5 + (i % 5 + 1) % 5]) & B[(i // 5) * 5 + (i % 5 + 2) % 5]) for i in range(25)]
            state[0] ^= _KECCAK_RC[rnd]
    return b"".join(state[i].to_bytes(8, "little") for i in range(4))


# ---------------------------------------------------------------------------
# Pure-Python secp256k1 (for key generation and EIP-712 signing)
# Only the operations needed: scalar mult, pubkey derivation, ECDSA sign.
# ---------------------------------------------------------------------------

_P  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def _modinv(a: int, m: int) -> int:
    """Extended Euclidean modular inverse."""
    g, x, _ = m, 1, 0
    r, s = a % m, 0
    while r:
        q = g // r
        g, r = r, g - q * r
        x, s = s, x - q * s
    return x % m


def _point_add(P: Optional[Tuple[int, int]], Q: Optional[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    if x1 == x2:
        if y1 != y2:
            return None
        # Point doubling
        lam = (3 * x1 * x1 * _modinv(2 * y1, _P)) % _P
    else:
        lam = ((y2 - y1) * _modinv(x2 - x1, _P)) % _P
    x3 = (lam * lam - x1 - x2) % _P
    y3 = (lam * (x1 - x3) - y1) % _P
    return x3, y3


def _scalar_mult(k: int, P: Tuple[int, int]) -> Tuple[int, int]:
    """Double-and-add scalar multiplication on secp256k1."""
    result: Optional[Tuple[int, int]] = None
    addend: Optional[Tuple[int, int]] = P
    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1
    assert result is not None
    return result


def _privkey_to_address(priv_bytes: bytes) -> str:
    """Derive checksummed Ethereum address from 32-byte private key."""
    priv_int = int.from_bytes(priv_bytes, "big")
    pub = _scalar_mult(priv_int, (_GX, _GY))
    pub_bytes = pub[0].to_bytes(32, "big") + pub[1].to_bytes(32, "big")
    addr_bytes = keccak256(pub_bytes)[12:]
    return _to_checksum_address(addr_bytes.hex())


def _to_checksum_address(addr_hex: str) -> str:
    """EIP-55 checksum encoding."""
    addr = addr_hex.lower().lstrip("0x")
    h = keccak256(addr.encode()).hex()
    return "0x" + "".join(c.upper() if int(h[i], 16) >= 8 else c for i, c in enumerate(addr))


def _ecdsa_sign(msg_hash: bytes, priv_bytes: bytes) -> Tuple[int, int, int]:
    """Sign a 32-byte message hash. Returns (v, r, s) — v is 0 or 1."""
    priv_int = int.from_bytes(priv_bytes, "big")
    z = int.from_bytes(msg_hash, "big")
    for _ in range(1000):
        k = int.from_bytes(secrets.token_bytes(32), "big") % (_N - 1) + 1
        point = _scalar_mult(k, (_GX, _GY))
        r = point[0] % _N
        if r == 0:
            continue
        s = (_modinv(k, _N) * (z + r * priv_int)) % _N
        if s == 0:
            continue
        v = point[1] & 1
        # Enforce low-s (EIP-2)
        if s > _N // 2:
            s = _N - s
            v ^= 1
        return v, r, s
    raise RuntimeError("ECDSA signing failed after 1000 attempts")


def _sign_to_hex(msg_hash: bytes, priv_bytes: bytes) -> str:
    """Return 65-byte Ethereum signature as 0x-prefixed hex (r, s, v)."""
    v, r, s = _ecdsa_sign(msg_hash, priv_bytes)
    r_bytes = r.to_bytes(32, "big")
    s_bytes = s.to_bytes(32, "big")
    v_byte = bytes([v + 27])
    return "0x" + (r_bytes + s_bytes + v_byte).hex()


# ---------------------------------------------------------------------------
# EIP-712 helpers for EIP-3009 TransferWithAuthorization
# ---------------------------------------------------------------------------

def _encode_uint256(n: int) -> bytes:
    return n.to_bytes(32, "big")


def _encode_address(addr: str) -> bytes:
    return bytes.fromhex(addr.lower().replace("0x", "").zfill(64))


def _encode_bytes32(b: bytes) -> bytes:
    assert len(b) == 32
    return b


def _keccak_str(s: str) -> bytes:
    return keccak256(s.encode())


def _eip712_domain_separator(name: str, version: str, chain_id: int, verifying_contract: str) -> bytes:
    """Compute the EIP-712 domain separator for a USDC-style contract."""
    type_hash = _keccak_str(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    )
    name_hash    = _keccak_str(name)
    version_hash = _keccak_str(version)
    encoded = (
        type_hash
        + name_hash
        + version_hash
        + _encode_uint256(chain_id)
        + _encode_address(verifying_contract)
    )
    return keccak256(encoded)


_TRANSFER_WITH_AUTH_TYPEHASH = _keccak_str(
    "TransferWithAuthorization(address from,address to,uint256 value,"
    "uint256 validAfter,uint256 validBefore,bytes32 nonce)"
)


def _eip712_transfer_hash(
    from_addr: str,
    to_addr: str,
    value: int,
    valid_after: int,
    valid_before: int,
    nonce: bytes,
) -> bytes:
    encoded = (
        _TRANSFER_WITH_AUTH_TYPEHASH
        + _encode_address(from_addr)
        + _encode_address(to_addr)
        + _encode_uint256(value)
        + _encode_uint256(valid_after)
        + _encode_uint256(valid_before)
        + _encode_bytes32(nonce)
    )
    return keccak256(encoded)


def _eip712_sign_transfer(
    domain_sep: bytes,
    from_addr: str,
    to_addr: str,
    value: int,
    valid_after: int,
    valid_before: int,
    nonce: bytes,
    priv_bytes: bytes,
) -> str:
    struct_hash = _eip712_transfer_hash(from_addr, to_addr, value, valid_after, valid_before, nonce)
    msg_hash = keccak256(b"\x19\x01" + domain_sep + struct_hash)
    return _sign_to_hex(msg_hash, priv_bytes)


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def _env_lookup(key: str) -> str:
    """Read key from env, then ~/.hermes/.env file."""
    val = os.environ.get(key, "")
    if val:
        return val
    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    dotenv_path = os.path.join(hermes_home, ".env")
    if os.path.isfile(dotenv_path):
        with open(dotenv_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + "="):
                    return line[len(key) + 1:].strip()
    return ""


def _get_private_key() -> bytes:
    raw = _env_lookup("X402_PRIVATE_KEY")
    if not raw:
        sys.stderr.write(
            "error: X402_PRIVATE_KEY not set.\n"
            "  Generate a key with: python3 x402_client.py wallet new\n"
            "  Then: export X402_PRIVATE_KEY=0x<key>\n"
            "  Or add to ~/.hermes/.env: X402_PRIVATE_KEY=0x<key>\n"
        )
        sys.exit(1)
    raw = raw.strip()
    if raw.startswith("0x") or raw.startswith("0X"):
        raw = raw[2:]
    try:
        key_bytes = bytes.fromhex(raw)
    except ValueError:
        sys.stderr.write("error: X402_PRIVATE_KEY is not valid hex.\n")
        sys.exit(1)
    if len(key_bytes) != 32:
        sys.stderr.write(f"error: X402_PRIVATE_KEY must be 32 bytes (got {len(key_bytes)}).\n")
        sys.exit(1)
    return key_bytes


def _get_facilitator_url() -> str:
    return _env_lookup("X402_FACILITATOR_URL") or DEFAULT_FACILITATOR


def _get_rpc_url(network_id: str) -> str:
    override = _env_lookup("X402_RPC_URL")
    if override:
        return override
    net = NETWORKS.get(network_id)
    if not net:
        sys.stderr.write(f"error: unsupported network '{network_id}'.\n")
        sys.exit(1)
    return net["rpc"]


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 20) -> Tuple[int, Any]:
    """GET a URL. Returns (status_code, parsed_body_or_None)."""
    req_headers = {"Accept": "application/json", "User-Agent": "x402_client/1.0"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return e.code, parsed


def _http_post(url: str, payload: Any, timeout: int = 30) -> Tuple[int, Any]:
    """POST JSON payload. Returns (status_code, parsed_body)."""
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "x402_client/1.0",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        return e.code, parsed


def _rpc_call(rpc_url: str, method: str, params: List[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    status, resp = _http_post(rpc_url, payload)
    if isinstance(resp, dict) and "error" in resp:
        raise RuntimeError(f"RPC error: {resp['error']}")
    if isinstance(resp, dict):
        return resp.get("result")
    raise RuntimeError(f"Unexpected RPC response (HTTP {status}): {resp}")


# ---------------------------------------------------------------------------
# x402 protocol helpers
# ---------------------------------------------------------------------------

def _decode_payment_required_header(header_value: str) -> Dict[str, Any]:
    """Decode a base64-encoded PAYMENT-REQUIRED header into a dict."""
    try:
        padded = header_value + "=" * (-len(header_value) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        return json.loads(decoded)
    except Exception as exc:
        raise ValueError(f"Failed to decode PAYMENT-REQUIRED header: {exc}") from exc


def _select_requirement(payment_required: Dict[str, Any]) -> Dict[str, Any]:
    """Select the first EVM exact requirement from accepts list."""
    accepts: List[Dict[str, Any]] = payment_required.get("accepts", [])
    if not accepts:
        raise ValueError("No payment requirements in 402 response.")
    # Prefer Base (eip155:8453) exact scheme
    for req in accepts:
        if req.get("scheme") == "exact" and req.get("network", "").startswith("eip155:"):
            if req.get("network") == DEFAULT_NETWORK:
                return req
    # Fall back to any EVM exact
    for req in accepts:
        if req.get("scheme") == "exact" and req.get("network", "").startswith("eip155:"):
            return req
    raise ValueError(
        f"No supported payment requirement found. "
        f"Available: {[r.get('scheme', '?') + '/' + r.get('network', '?') for r in accepts]}"
    )


def _build_payment_payload(
    requirement: Dict[str, Any],
    resource_url: str,
    priv_bytes: bytes,
) -> Dict[str, Any]:
    """Build a signed x402 v2 PaymentPayload for the exact EVM scheme."""
    network_id = requirement["network"]
    net = NETWORKS.get(network_id)
    if not net:
        raise ValueError(f"Unsupported network '{network_id}'.")

    from_addr   = _privkey_to_address(priv_bytes)
    to_addr     = requirement["payTo"]
    amount      = int(requirement["amount"])
    max_timeout = int(requirement.get("maxTimeoutSeconds", 60))
    asset_addr  = requirement["asset"]

    # Use token name/version from requirement extra if available
    extra = requirement.get("extra", {})
    token_name    = extra.get("name", net["usdc_name"])
    token_version = extra.get("version", net["usdc_version"])
    chain_id      = net["chain_id"]

    now          = int(time.time())
    valid_after  = now - 1          # immediately valid
    valid_before = now + max_timeout

    nonce = secrets.token_bytes(32)

    domain_sep = _eip712_domain_separator(token_name, token_version, chain_id, asset_addr)
    signature  = _eip712_sign_transfer(
        domain_sep, from_addr, to_addr, amount,
        valid_after, valid_before, nonce, priv_bytes,
    )

    authorization = {
        "from":        from_addr,
        "to":          to_addr,
        "value":       str(amount),
        "validAfter":  str(valid_after),
        "validBefore": str(valid_before),
        "nonce":       "0x" + nonce.hex(),
    }

    payload: Dict[str, Any] = {
        "x402Version": 2,
        "resource": {
            "url": resource_url,
        },
        "accepted": requirement,
        "payload": {
            "signature":     signature,
            "authorization": authorization,
        },
        "extensions": {},
    }
    return payload


def _encode_payment_payload(payload: Dict[str, Any]) -> str:
    """Base64-encode a payment payload for the PAYMENT-SIGNATURE header."""
    return base64.b64encode(json.dumps(payload).encode()).decode()


# ---------------------------------------------------------------------------
# USDC balance via RPC
# ---------------------------------------------------------------------------

def _usdc_balance(address: str, network_id: str) -> int:
    """Return raw USDC balance (6-decimal integer) for address on network."""
    net = NETWORKS.get(network_id)
    if not net:
        raise ValueError(f"Unsupported network '{network_id}'.")
    rpc_url  = _get_rpc_url(network_id)
    usdc_addr = net["usdc"]
    # balanceOf(address) = 0x70a08231
    padded_addr = address.lower().replace("0x", "").zfill(64)
    data = "0x70a08231" + padded_addr
    result = _rpc_call(rpc_url, "eth_call", [{"to": usdc_addr, "data": data}, "latest"])
    if not result or result == "0x":
        return 0
    return int(result, 16)


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def cmd_wallet_new(_args: argparse.Namespace) -> None:
    """Generate a fresh secp256k1 keypair for use as an agent wallet."""
    priv_bytes = secrets.token_bytes(32)
    # Ensure the key is in range [1, N-1]
    priv_int = int.from_bytes(priv_bytes, "big")
    while priv_int == 0 or priv_int >= _N:
        priv_bytes = secrets.token_bytes(32)
        priv_int   = int.from_bytes(priv_bytes, "big")

    address = _privkey_to_address(priv_bytes)
    _print_json({
        "private_key": "0x" + priv_bytes.hex(),
        "address":     address,
        "warning":     "Save private_key immediately — it will not be shown again.",
    })


def cmd_wallet_address(_args: argparse.Namespace) -> None:
    """Print the Ethereum address derived from X402_PRIVATE_KEY."""
    priv_bytes = _get_private_key()
    address    = _privkey_to_address(priv_bytes)
    _print_json({"address": address})


def cmd_wallet_balance(args: argparse.Namespace) -> None:
    """Check USDC balance for the configured wallet on a given network."""
    priv_bytes = _get_private_key()
    address    = _privkey_to_address(priv_bytes)
    network_id = args.network

    raw_balance = _usdc_balance(address, network_id)
    human       = raw_balance / 1_000_000  # USDC has 6 decimals

    net = NETWORKS[network_id]
    _print_json({
        "address":         address,
        "network":         network_id,
        "network_name":    net["name"],
        "usdc_contract":   net["usdc"],
        "balance_raw":     raw_balance,
        "balance_usdc":    round(human, 6),
    })


def cmd_probe(args: argparse.Namespace) -> None:
    """Probe a URL for x402 payment requirements (no payment sent)."""
    url = args.url
    status, body = _http_get(url)

    if status != 402:
        _print_json({
            "url":    url,
            "status": status,
            "note":   "Resource did not return 402. May not be x402-protected.",
            "body":   body,
        })
        return

    # body is the JSON decoded 402 response
    if isinstance(body, dict):
        payment_required = body
    else:
        _print_json({
            "url":    url,
            "status": 402,
            "note":   "Got 402 but body is not JSON.",
            "body":   body,
        })
        return

    accepts = payment_required.get("accepts", [])
    _print_json({
        "url":              url,
        "status":           402,
        "x402Version":      payment_required.get("x402Version"),
        "error":            payment_required.get("error"),
        "resource":         payment_required.get("resource"),
        "accepts":          accepts,
        "extensions":       payment_required.get("extensions"),
        "requirements_count": len(accepts),
    })


def cmd_inspect(args: argparse.Namespace) -> None:
    """Show raw headers from a URL (useful for debugging 402 responses)."""
    url = args.url
    req = urllib.request.Request(url, headers={"User-Agent": "x402_client/1.0"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            hdrs = dict(resp.headers)
            _print_json({"url": url, "status": resp.status, "headers": hdrs})
    except urllib.error.HTTPError as e:
        hdrs = dict(e.headers) if e.headers else {}
        _print_json({"url": url, "status": e.code, "headers": hdrs})


def cmd_verify(args: argparse.Namespace) -> None:
    """Build a payment payload and verify it against the facilitator (no settlement)."""
    url        = args.url
    priv_bytes = _get_private_key()

    # Step 1: Probe for requirements
    status, body = _http_get(url)
    if status != 402:
        _print_json({"error": f"Expected 402 from {url}, got {status}.", "body": body})
        sys.exit(1)

    if not isinstance(body, dict):
        _print_json({"error": "402 response body is not JSON.", "body": body})
        sys.exit(1)

    payment_required = body
    try:
        requirement = _select_requirement(payment_required)
    except ValueError as exc:
        _print_json({"error": str(exc)})
        sys.exit(1)

    # Step 2: Build payload
    try:
        payload = _build_payment_payload(requirement, url, priv_bytes)
    except Exception as exc:
        _print_json({"error": f"Failed to build payment payload: {exc}"})
        sys.exit(1)

    # Step 3: Verify with facilitator
    facilitator_url = _get_facilitator_url()
    verify_body = {
        "payload":     payload,
        "requirements": requirement,
    }
    v_status, v_resp = _http_post(f"{facilitator_url}/verify", verify_body)

    _print_json({
        "url":             url,
        "network":         requirement.get("network"),
        "amount_raw":      requirement.get("amount"),
        "amount_usdc":     round(int(requirement.get("amount", "0")) / 1_000_000, 6),
        "pay_to":          requirement.get("payTo"),
        "from":            payload["payload"]["authorization"]["from"],
        "facilitator_url": facilitator_url,
        "verify_status":   v_status,
        "verify_response": v_resp,
    })


def cmd_pay(args: argparse.Namespace) -> None:
    """Pay an x402-protected URL (probe → sign → settle → fetch resource)."""
    url        = args.url
    priv_bytes = _get_private_key()

    # Step 1: Probe
    status, body = _http_get(url)
    if status != 402:
        if status == 200:
            _print_json({"url": url, "status": 200, "note": "Resource is free.", "body": body})
            return
        _print_json({"error": f"Expected 402 from {url}, got {status}.", "body": body})
        sys.exit(1)

    if not isinstance(body, dict):
        _print_json({"error": "402 response body is not JSON.", "body": body})
        sys.exit(1)

    payment_required = body
    try:
        requirement = _select_requirement(payment_required)
    except ValueError as exc:
        _print_json({"error": str(exc)})
        sys.exit(1)

    # Step 2: Build + sign payload
    try:
        payload = _build_payment_payload(requirement, url, priv_bytes)
    except Exception as exc:
        _print_json({"error": f"Failed to build payment payload: {exc}"})
        sys.exit(1)

    encoded_payload = _encode_payment_payload(payload)

    # Step 3: Re-request resource with PAYMENT-SIGNATURE header
    pay_status, pay_body = _http_get(url, headers={"PAYMENT-SIGNATURE": encoded_payload})

    if pay_status == 200:
        _print_json({
            "url":         url,
            "status":      200,
            "network":     requirement.get("network"),
            "amount_usdc": round(int(requirement.get("amount", "0")) / 1_000_000, 6),
            "from":        payload["payload"]["authorization"]["from"],
            "pay_to":      requirement.get("payTo"),
            "response":    pay_body,
        })
    else:
        _print_json({
            "url":         url,
            "status":      pay_status,
            "error":       "Payment rejected or resource error.",
            "body":        pay_body,
        })
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    network_choices = list(NETWORKS.keys())

    parser = argparse.ArgumentParser(
        prog="x402_client",
        description="x402 payment protocol CLI — stdlib only, zero dependencies.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # -- wallet --
    p_wallet = sub.add_parser("wallet", help="Wallet management (new, address, balance)")
    wallet_sub = p_wallet.add_subparsers(dest="wallet_cmd", metavar="SUBCOMMAND")
    wallet_sub.required = True

    wallet_sub.add_parser("new", help="Generate a new secp256k1 keypair")
    wallet_sub.add_parser("address", help="Show address for X402_PRIVATE_KEY")

    p_balance = wallet_sub.add_parser("balance", help="Check USDC balance on a network")
    p_balance.add_argument(
        "--network", default=DEFAULT_NETWORK, choices=network_choices,
        help=f"Network CAIP-2 ID (default: {DEFAULT_NETWORK})",
    )

    # -- probe --
    p_probe = sub.add_parser("probe", help="Probe URL for x402 payment requirements")
    p_probe.add_argument("url", help="URL to probe")

    # -- inspect --
    p_inspect = sub.add_parser("inspect", help="Show raw HTTP headers from URL")
    p_inspect.add_argument("url", help="URL to inspect")

    # -- verify --
    p_verify = sub.add_parser("verify", help="Verify payment payload (no settlement)")
    p_verify.add_argument("url", help="x402-protected URL")

    # -- pay --
    p_pay = sub.add_parser("pay", help="Pay for and fetch an x402-protected resource")
    p_pay.add_argument("url", help="x402-protected URL")

    return parser


WALLET_DISPATCH = {
    "new":     cmd_wallet_new,
    "address": cmd_wallet_address,
    "balance": cmd_wallet_balance,
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args   = parser.parse_args(argv)

    try:
        if args.command == "wallet":
            fn = WALLET_DISPATCH.get(args.wallet_cmd)
            if fn is None:
                _print_json({"error": f"Unknown wallet subcommand '{args.wallet_cmd}'"})
                return 1
            fn(args)
        elif args.command == "probe":
            cmd_probe(args)
        elif args.command == "inspect":
            cmd_inspect(args)
        elif args.command == "verify":
            cmd_verify(args)
        elif args.command == "pay":
            cmd_pay(args)
        else:
            _print_json({"error": f"Unknown command '{args.command}'"})
            return 1
    except KeyboardInterrupt:
        _print_json({"error": "Interrupted by user"})
        return 130
    except SystemExit:
        raise
    except Exception as exc:
        _print_json({"error": str(exc)})
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
