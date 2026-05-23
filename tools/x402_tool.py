#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""x402 payment tools using the official x402 Python SDK.

Provides:
- x402_pay: Make a paid HTTP request to any x402 endpoint
- x402_balance: Check wallet USDC balance on Base
- x402_wallet: Show wallet address

Requires: ``pip install hermes-agent[x402]``
"""

import base64
import json
import os
from pathlib import Path

from tools.registry import registry


def _check_x402() -> bool:
    """Return True when the x402 SDK is importable."""
    try:
        import x402  # noqa: F401

        return True
    except ImportError:
        return False


def _get_signer():
    """Resolve signer from env vars or ~/.hermes-x402/wallet.json."""
    from eth_account import Account
    from x402.mechanisms.evm.signers import EthAccountSigner

    key = os.environ.get("X402_PRIVATE_KEY") or os.environ.get("EVM_PRIVATE_KEY")
    if not key:
        wallet_file = Path.home() / ".hermes-x402" / "wallet.json"
        if wallet_file.exists():
            data = json.loads(wallet_file.read_text(encoding="utf-8"))
            key = data.get("privateKey") or data.get("private_key")

    if not key:
        raise RuntimeError("No x402 wallet configured. Run: hermes setup x402")

    account = Account.from_key(key)
    return EthAccountSigner(account), account.address


def x402_pay(url: str, method: str = "GET", body: str = "", headers: str = "") -> str:
    """Make an x402-paid HTTP request. Payment is handled automatically."""
    if not _check_x402():
        return json.dumps(
            {"error": "x402 SDK not installed. Run: pip install hermes-agent[x402]"}
        )

    if not str(url or "").strip():
        return json.dumps({"error": "url is required"})

    try:
        from x402 import x402ClientSync
        from x402.mechanisms.evm.exact.register import register_exact_evm_client_sync

        signer, _address = _get_signer()
        client = x402ClientSync()
        register_exact_evm_client_sync(client, signer)

        import httpx

        req_headers = json.loads(headers) if headers else {}
        if not isinstance(req_headers, dict):
            return json.dumps({"error": "headers must be a JSON object"})

        upper_method = method.upper()
        req_body = body if body and upper_method not in {"GET", "HEAD", "DELETE"} else None

        with httpx.Client() as http:
            from x402.http.clients.httpx import wrapHttpxSyncWithPayment

            wrapped = wrapHttpxSyncWithPayment(client, http)
            response = wrapped.request(
                upper_method,
                url,
                headers=req_headers,
                content=req_body,
            )

        result = {
            "status": response.status_code,
            "body": response.text[:4000],
            "payment": None,
        }
        payment_header = response.headers.get("payment-response")
        if payment_header:
            try:
                decoded = base64.b64decode(payment_header)
                result["payment"] = json.loads(decoded)
            except Exception:
                result["payment"] = None

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def x402_balance() -> str:
    """Check wallet USDC balance on Base mainnet."""
    if not _check_x402():
        return json.dumps(
            {"error": "x402 SDK not installed. Run: pip install hermes-agent[x402]"}
        )

    try:
        _signer, address = _get_signer()

        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"),
            abi=[
                {
                    "inputs": [{"name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function",
                }
            ],
        )
        balance = usdc.functions.balanceOf(Web3.to_checksum_address(address)).call()
        return json.dumps(
            {
                "address": address,
                "usdc_balance": balance / 1e6,
                "network": "base",
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


def x402_wallet() -> str:
    """Show wallet address for the active x402 signer."""
    try:
        _signer, address = _get_signer()
        return json.dumps({"address": address, "network": "base"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


X402_PAY_SCHEMA = {
    "name": "x402_pay",
    "description": (
        "Make a paid HTTP request to any x402 endpoint. "
        "Payment is automatic from your wallet in USDC on Base."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The x402 endpoint URL",
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                "default": "GET",
            },
            "body": {
                "type": "string",
                "description": "JSON request body (for POST/PUT/PATCH only)",
            },
            "headers": {
                "type": "string",
                "description": "JSON headers object",
            },
        },
        "required": ["url"],
    },
}

X402_BALANCE_SCHEMA = {
    "name": "x402_balance",
    "description": "Check your x402 wallet USDC balance on Base.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}

X402_WALLET_SCHEMA = {
    "name": "x402_wallet",
    "description": "Show your x402 wallet address.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


def _handle_x402_pay(args, **kwargs):
    return x402_pay(
        url=str(args.get("url", "")),
        method=str(args.get("method", "GET")),
        body=str(args.get("body", "")),
        headers=str(args.get("headers", "")),
    )


def _handle_x402_balance(args, **kwargs):
    return x402_balance()


def _handle_x402_wallet(args, **kwargs):
    return x402_wallet()


registry.register(
    name="x402_pay",
    toolset="x402",
    schema=X402_PAY_SCHEMA,
    handler=_handle_x402_pay,
    check_fn=_check_x402,
)

registry.register(
    name="x402_balance",
    toolset="x402",
    schema=X402_BALANCE_SCHEMA,
    handler=_handle_x402_balance,
    check_fn=_check_x402,
)

registry.register(
    name="x402_wallet",
    toolset="x402",
    schema=X402_WALLET_SCHEMA,
    handler=_handle_x402_wallet,
    check_fn=_check_x402,
)
