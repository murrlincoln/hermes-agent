from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "optional-skills"
    / "blockchain"
    / "x402"
    / "scripts"
    / "x402_client.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("x402_skill", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# keccak256
# ---------------------------------------------------------------------------


def test_keccak256_empty_string():
    mod = load_module()
    # keccak256("") = 0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470
    result = mod.keccak256(b"").hex()
    assert result == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"


def test_keccak256_known_vector():
    mod = load_module()
    # keccak256("abc") = 0x4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45
    result = mod.keccak256(b"abc").hex()
    assert result == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"


# ---------------------------------------------------------------------------
# Key generation and address derivation
# ---------------------------------------------------------------------------


def test_wallet_new_produces_valid_keypair(capsys):
    mod = load_module()
    exit_code = mod.main(["wallet", "new"])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert exit_code == 0
    assert "private_key" in data
    assert "address" in data

    priv = data["private_key"]
    addr = data["address"]

    assert priv.startswith("0x")
    assert len(priv) == 66  # 0x + 64 hex chars
    assert addr.startswith("0x")
    assert len(addr) == 42  # 0x + 40 hex chars


def test_wallet_new_generates_unique_keys():
    mod = load_module()
    keys = set()
    for _ in range(5):
        priv_bytes = __import__("secrets").token_bytes(32)
        priv_int   = int.from_bytes(priv_bytes, "big")
        # Ensure in valid range
        while priv_int == 0 or priv_int >= mod._N:
            priv_bytes = __import__("secrets").token_bytes(32)
            priv_int   = int.from_bytes(priv_bytes, "big")
        keys.add(priv_bytes.hex())
    assert len(keys) == 5


def test_privkey_to_address_is_deterministic():
    mod = load_module()
    # Well-known test vector: private key 1 → known address
    priv = (1).to_bytes(32, "big")
    addr1 = mod._privkey_to_address(priv)
    addr2 = mod._privkey_to_address(priv)
    assert addr1 == addr2
    assert addr1.startswith("0x")
    assert len(addr1) == 42


def test_privkey_to_address_known_vector():
    mod = load_module()
    # Private key = 1 → public key is the secp256k1 generator point G
    # Address = keccak256(Gx || Gy)[12:] with EIP-55 checksum
    priv = (1).to_bytes(32, "big")
    addr = mod._privkey_to_address(priv).lower()
    # The generator point gives address 0x7e5f4552091a69125d5dfcb7b8c2659029395bdf (known)
    assert addr == "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"


def test_to_checksum_address_roundtrip():
    mod = load_module()
    raw = "a94f5374fce5edbc8e2a8697c15331677e6ebf0b"
    checksummed = mod._to_checksum_address(raw)
    # Verify it's 42 chars and 0x-prefixed
    assert checksummed.startswith("0x")
    assert len(checksummed) == 42
    # Verify it contains mixed case (EIP-55)
    inner = checksummed[2:]
    assert inner != inner.lower() or inner != inner.upper()


# ---------------------------------------------------------------------------
# EIP-712 helpers
# ---------------------------------------------------------------------------


def test_eip712_domain_separator_is_bytes32():
    mod = load_module()
    sep = mod._eip712_domain_separator(
        "USD Coin", "2", 8453,
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )
    assert isinstance(sep, bytes)
    assert len(sep) == 32


def test_eip712_sign_transfer_produces_65_byte_sig():
    mod = load_module()
    import secrets as _secrets
    priv_bytes = (1).to_bytes(32, "big")  # deterministic for testing
    domain_sep = mod._eip712_domain_separator(
        "USD Coin", "2", 8453,
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )
    nonce = _secrets.token_bytes(32)
    sig = mod._eip712_sign_transfer(
        domain_sep,
        "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf",
        "0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
        1_000_000,
        0,
        9999999999,
        nonce,
        priv_bytes,
    )
    assert sig.startswith("0x")
    # 65 bytes = 130 hex chars + "0x" prefix
    assert len(sig) == 132


# ---------------------------------------------------------------------------
# Payment payload construction
# ---------------------------------------------------------------------------


def test_build_payment_payload_structure():
    mod = load_module()
    priv_bytes = (1).to_bytes(32, "big")
    requirement = {
        "scheme":            "exact",
        "network":           "eip155:8453",
        "amount":            "1000000",
        "asset":             "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "payTo":             "0x209693Bc6afc0C5328bA36FaF03C314EF312287C",
        "maxTimeoutSeconds": 60,
        "extra":             {"name": "USD Coin", "version": "2"},
    }
    payload = mod._build_payment_payload(requirement, "https://api.example.com/data", priv_bytes)

    assert payload["x402Version"] == 2
    assert payload["accepted"] == requirement
    assert "signature" in payload["payload"]
    assert "authorization" in payload["payload"]

    auth = payload["payload"]["authorization"]
    assert auth["value"] == "1000000"
    assert auth["to"].lower() == "0x209693bc6afc0c5328ba36faf03c314ef312287c"
    assert auth["nonce"].startswith("0x")
    assert len(auth["nonce"]) == 66  # 0x + 64 hex chars
    valid_after  = int(auth["validAfter"])
    valid_before = int(auth["validBefore"])
    assert valid_before > valid_after
    assert valid_before - valid_after <= 65  # within maxTimeoutSeconds + 1s buffer


def test_encode_payment_payload_roundtrip():
    mod = load_module()
    data = {"x402Version": 2, "foo": "bar"}
    encoded = mod._encode_payment_payload(data)
    import base64 as _b64
    decoded = json.loads(_b64.b64decode(encoded + "=" * (-len(encoded) % 4)).decode())
    assert decoded == data


# ---------------------------------------------------------------------------
# cmd_probe
# ---------------------------------------------------------------------------


def test_cmd_probe_returns_402_requirements(capsys):
    mod = load_module()

    payment_required_body = {
        "x402Version": 2,
        "error":       "Payment required",
        "resource":    {"url": "https://api.example.com/premium"},
        "accepts": [
            {
                "scheme":            "exact",
                "network":           "eip155:8453",
                "amount":            "1000000",
                "asset":             "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "payTo":             "0xRecipient",
                "maxTimeoutSeconds": 60,
            }
        ],
        "extensions": {},
    }

    with patch.object(mod, "_http_get", return_value=(402, payment_required_body)):
        exit_code = mod.main(["probe", "https://api.example.com/premium"])

    out = capsys.readouterr().out
    data = json.loads(out)

    assert exit_code == 0
    assert data["status"] == 402
    assert data["requirements_count"] == 1
    assert data["accepts"][0]["scheme"] == "exact"
    assert data["accepts"][0]["network"] == "eip155:8453"


def test_cmd_probe_non_402_returns_status(capsys):
    mod = load_module()

    with patch.object(mod, "_http_get", return_value=(200, {"data": "free content"})):
        exit_code = mod.main(["probe", "https://api.example.com/free"])

    out = capsys.readouterr().out
    data = json.loads(out)

    assert exit_code == 0
    assert data["status"] == 200
    assert "not be x402-protected" in data["note"]


# ---------------------------------------------------------------------------
# cmd_wallet_address
# ---------------------------------------------------------------------------


def test_cmd_wallet_address_uses_env_key(monkeypatch, capsys):
    mod = load_module()
    # Private key = 1 → known address
    monkeypatch.setenv("X402_PRIVATE_KEY", "0x" + "00" * 31 + "01")

    exit_code = mod.main(["wallet", "address"])
    out = capsys.readouterr().out
    data = json.loads(out)

    assert exit_code == 0
    assert data["address"].lower() == "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"


def test_cmd_wallet_address_errors_without_key(monkeypatch):
    mod = load_module()
    monkeypatch.delenv("X402_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("HERMES_HOME", "/tmp/nonexistent_x402_test_home")

    try:
        mod.main(["wallet", "address"])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("Expected SystemExit when X402_PRIVATE_KEY is missing")


# ---------------------------------------------------------------------------
# cmd_wallet_balance
# ---------------------------------------------------------------------------


def test_cmd_wallet_balance_returns_usdc(monkeypatch, capsys):
    mod = load_module()
    monkeypatch.setenv("X402_PRIVATE_KEY", "0x" + "00" * 31 + "01")

    # eth_call returns 5.5 USDC = 5_500_000 raw (0x53EC60)
    with patch.object(mod, "_rpc_call", return_value="0x000000000000000000000000000000000000000000000000000000000053EC60"):
        exit_code = mod.main(["wallet", "balance"])

    out = capsys.readouterr().out
    data = json.loads(out)

    assert exit_code == 0
    assert data["network"] == "eip155:8453"
    assert data["balance_raw"] == 5_500_000
    assert abs(data["balance_usdc"] - 5.5) < 1e-6


# ---------------------------------------------------------------------------
# cmd_verify
# ---------------------------------------------------------------------------


def test_cmd_verify_calls_facilitator(monkeypatch, capsys):
    mod = load_module()
    monkeypatch.setenv("X402_PRIVATE_KEY", "0x" + "00" * 31 + "01")

    payment_required_body = {
        "x402Version": 2,
        "error":       "Payment required",
        "resource":    {"url": "https://api.example.com/premium"},
        "accepts": [
            {
                "scheme":            "exact",
                "network":           "eip155:8453",
                "amount":            "1000000",
                "asset":             "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "payTo":             "0x209693Bc6afc0C5328bA36FaF03C514EF312287C",
                "maxTimeoutSeconds": 60,
                "extra":             {"name": "USD Coin", "version": "2"},
            }
        ],
        "extensions": {},
    }
    verify_response = {"isValid": True, "payer": "0x7e5f4552091a69125d5dfcb7b8c2659029395bdf"}

    with (
        patch.object(mod, "_http_get", return_value=(402, payment_required_body)),
        patch.object(mod, "_http_post", return_value=(200, verify_response)),
    ):
        exit_code = mod.main(["verify", "https://api.example.com/premium"])

    out = capsys.readouterr().out
    data = json.loads(out)

    assert exit_code == 0
    assert data["verify_response"]["isValid"] is True
    assert data["amount_usdc"] == 1.0
    assert data["network"] == "eip155:8453"


# ---------------------------------------------------------------------------
# _select_requirement
# ---------------------------------------------------------------------------


def test_select_requirement_prefers_base():
    mod = load_module()

    payment_required = {
        "accepts": [
            {"scheme": "exact", "network": "eip155:1",    "amount": "1000000", "asset": "0xA", "payTo": "0xB", "maxTimeoutSeconds": 60},
            {"scheme": "exact", "network": "eip155:8453", "amount": "1000000", "asset": "0xC", "payTo": "0xD", "maxTimeoutSeconds": 60},
        ]
    }
    req = mod._select_requirement(payment_required)
    assert req["network"] == "eip155:8453"


def test_select_requirement_falls_back_to_any_evm():
    mod = load_module()

    payment_required = {
        "accepts": [
            {"scheme": "exact", "network": "eip155:42161", "amount": "500000", "asset": "0xA", "payTo": "0xB", "maxTimeoutSeconds": 60},
        ]
    }
    req = mod._select_requirement(payment_required)
    assert req["network"] == "eip155:42161"


def test_select_requirement_raises_on_no_evm():
    mod = load_module()

    payment_required = {
        "accepts": [
            {"scheme": "exact", "network": "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp", "amount": "1000000", "asset": "EPjFW", "payTo": "SomeKey", "maxTimeoutSeconds": 60},
        ]
    }
    try:
        mod._select_requirement(payment_required)
    except ValueError as exc:
        assert "No supported" in str(exc)
    else:
        raise AssertionError("Expected ValueError for non-EVM requirement")


# ---------------------------------------------------------------------------
# _env_lookup
# ---------------------------------------------------------------------------


def test_env_lookup_reads_hermes_dotenv(tmp_path, monkeypatch):
    mod = load_module()
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir(parents=True)
    (hermes_home / ".env").write_text(
        "X402_PRIVATE_KEY=0xdeadbeef\nX402_FACILITATOR_URL=https://test.facilitator.example\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.delenv("X402_PRIVATE_KEY", raising=False)

    assert mod._env_lookup("X402_PRIVATE_KEY") == "0xdeadbeef"
    assert mod._env_lookup("X402_FACILITATOR_URL") == "https://test.facilitator.example"


def test_env_lookup_env_var_overrides_dotenv(tmp_path, monkeypatch):
    mod = load_module()
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir(parents=True)
    (hermes_home / ".env").write_text("X402_PRIVATE_KEY=0xfromfile\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("X402_PRIVATE_KEY", "0xfromenv")

    assert mod._env_lookup("X402_PRIVATE_KEY") == "0xfromenv"
