"""Tests for tools/x402_tool.py."""

from __future__ import annotations

import base64
import builtins
import json
import sys
import types


def _install_fake_signer_modules(monkeypatch, address: str = "0xabc") -> None:
    eth_account_module = types.ModuleType("eth_account")

    class _FakeAccountObj:
        def __init__(self, wallet_address: str):
            self.address = wallet_address

    class _FakeAccount:
        @staticmethod
        def from_key(_key):
            return _FakeAccountObj(address)

    setattr(eth_account_module, "Account", _FakeAccount)

    x402_module = types.ModuleType("x402")
    mechanisms_module = types.ModuleType("x402.mechanisms")
    evm_module = types.ModuleType("x402.mechanisms.evm")
    signers_module = types.ModuleType("x402.mechanisms.evm.signers")

    class _FakeEthAccountSigner:
        def __init__(self, account):
            self.account = account

    setattr(signers_module, "EthAccountSigner", _FakeEthAccountSigner)

    monkeypatch.setitem(sys.modules, "eth_account", eth_account_module)
    monkeypatch.setitem(sys.modules, "x402", x402_module)
    monkeypatch.setitem(sys.modules, "x402.mechanisms", mechanisms_module)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.evm", evm_module)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.evm.signers", signers_module)


def test_check_x402_returns_false_when_sdk_missing(monkeypatch):
    from tools import x402_tool

    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "x402":
            raise ImportError("x402 not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert x402_tool._check_x402() is False


def test_x402_wallet_returns_address_from_wallet_file(monkeypatch, tmp_path):
    from tools import x402_tool

    _install_fake_signer_modules(monkeypatch, address="0xwallet")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("X402_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("EVM_PRIVATE_KEY", raising=False)

    wallet_dir = tmp_path / ".hermes-x402"
    wallet_dir.mkdir(parents=True)
    (wallet_dir / "wallet.json").write_text(
        json.dumps({"privateKey": "0xprivate"}),
        encoding="utf-8",
    )

    result = json.loads(x402_tool.x402_wallet())
    assert result["address"] == "0xwallet"
    assert result["network"] == "base"


def test_x402_balance_mocks_web3_call(monkeypatch):
    from tools import x402_tool

    monkeypatch.setattr(x402_tool, "_check_x402", lambda: True)
    monkeypatch.setattr(x402_tool, "_get_signer", lambda: (object(), "0xabc"))

    web3_module = types.ModuleType("web3")

    class _FakeBalanceFn:
        def balanceOf(self, _address):
            return self

        def call(self):
            return 1_250_000

    class _FakeContract:
        functions = _FakeBalanceFn()

    class _FakeEth:
        def contract(self, address, abi):
            return _FakeContract()

    class _FakeWeb3:
        def __init__(self, _provider):
            self.eth = _FakeEth()

        @staticmethod
        def HTTPProvider(url):
            return url

        @staticmethod
        def to_checksum_address(value):
            return value

    setattr(web3_module, "Web3", _FakeWeb3)
    monkeypatch.setitem(sys.modules, "web3", web3_module)

    result = json.loads(x402_tool.x402_balance())
    assert result["address"] == "0xabc"
    assert result["network"] == "base"
    assert result["usdc_balance"] == 1.25


def test_x402_pay_mocks_httpx_response(monkeypatch):
    from tools import x402_tool

    monkeypatch.setattr(x402_tool, "_check_x402", lambda: True)
    monkeypatch.setattr(x402_tool, "_get_signer", lambda: (object(), "0xabc"))

    payment_payload = {"txHash": "0x123"}
    payment_header = base64.b64encode(
        json.dumps(payment_payload).encode("utf-8")
    ).decode("utf-8")

    captured = {}

    x402_module = types.ModuleType("x402")

    class _FakeClient:
        pass

    setattr(x402_module, "x402ClientSync", _FakeClient)

    mechanisms_module = types.ModuleType("x402.mechanisms")
    evm_module = types.ModuleType("x402.mechanisms.evm")
    exact_module = types.ModuleType("x402.mechanisms.evm.exact")
    register_module = types.ModuleType("x402.mechanisms.evm.exact.register")
    setattr(
        register_module,
        "register_exact_evm_client_sync",
        lambda _client, _signer: None,
    )

    http_pkg = types.ModuleType("x402.http")
    clients_pkg = types.ModuleType("x402.http.clients")
    httpx_wrap_module = types.ModuleType("x402.http.clients.httpx")

    class _FakeResponse:
        status_code = 200
        text = "ok"
        headers = {"payment-response": payment_header}

    class _WrappedClient:
        def request(self, method, url, headers=None, content=None):
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = headers
            captured["content"] = content
            return _FakeResponse()

    setattr(
        httpx_wrap_module,
        "wrapHttpxSyncWithPayment",
        lambda _client, _http: _WrappedClient(),
    )

    httpx_module = types.ModuleType("httpx")

    class _FakeHttpxClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    setattr(httpx_module, "Client", _FakeHttpxClient)

    monkeypatch.setitem(sys.modules, "x402", x402_module)
    monkeypatch.setitem(sys.modules, "x402.mechanisms", mechanisms_module)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.evm", evm_module)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.evm.exact", exact_module)
    monkeypatch.setitem(sys.modules, "x402.mechanisms.evm.exact.register", register_module)
    monkeypatch.setitem(sys.modules, "x402.http", http_pkg)
    monkeypatch.setitem(sys.modules, "x402.http.clients", clients_pkg)
    monkeypatch.setitem(sys.modules, "x402.http.clients.httpx", httpx_wrap_module)
    monkeypatch.setitem(sys.modules, "httpx", httpx_module)

    result = json.loads(
        x402_tool.x402_pay(
            url="https://example.com/paid",
            method="post",
            body='{"hello":"world"}',
            headers='{"x-test":"1"}',
        )
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://example.com/paid"
    assert captured["headers"] == {"x-test": "1"}
    assert captured["content"] == '{"hello":"world"}'
    assert result["status"] == 200
    assert result["payment"] == payment_payload
