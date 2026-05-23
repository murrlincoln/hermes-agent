#!/usr/bin/env python3
"""x402 Discovery Agent — search, test, and recommend x402 endpoints.

Aggregates three sources:
  - CDP Bazaar (api.cdp.coinbase.com)
  - agentic.market (api.agentic.market)
  - x402-list.com (x402-list.com)

Usage:
  python3 discovery.py search "web search"
  python3 discovery.py list --source bazaar --limit 20
  python3 discovery.py test "https://api.exa.ai/search"
  python3 discovery.py howto "https://api.exa.ai/search"
  python3 discovery.py recommend "I need crypto prices"
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Any

BAZAAR_URL = "https://api.cdp.coinbase.com/platform/v2/x402/discovery/resources"
AGENTIC_URL = "https://api.agentic.market/v1/services"
X402LIST_URL = "https://x402-list.com/api/v1/services"

KNOWN_ENDPOINTS: dict[str, dict[str, Any]] = {
    "https://wolframalpha.x402.paysponge.com/v1/result": {
        "name": "Wolfram Alpha",
        "method": "GET",
        "example_url": "https://wolframalpha.x402.paysponge.com/v1/result?i=population+of+france",
        "price": "$0.01",
        "category": "computation",
        "notes": "Query param is 'i', URL-encode spaces as +",
    },
    "https://api.exa.ai/search": {
        "name": "Exa Search",
        "method": "POST",
        "example_body": '{"query":"search term","numResults":5,"type":"auto"}',
        "example_headers": '{"Content-Type":"application/json"}',
        "price": "$0.007",
        "category": "search",
    },
    "https://pplx.x402.paysponge.com/search": {
        "name": "Perplexity",
        "method": "POST",
        "example_body": '{"query":"your question"}',
        "example_headers": '{"Content-Type":"application/json"}',
        "price": "$0.01",
        "category": "search",
    },
    "https://pro-api.coingecko.com/api/v3/x402/simple/price": {
        "name": "CoinGecko Prices",
        "method": "GET",
        "example_url": "https://pro-api.coingecko.com/api/v3/x402/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true",
        "price": "$0.01",
        "category": "data",
    },
    "https://blockrun.ai/api/v1/defillama/prices": {
        "name": "BlockRun DeFi Prices",
        "method": "GET",
        "example_url": "https://blockrun.ai/api/v1/defillama/prices/coingecko:bitcoin,coingecko:ethereum",
        "price": "$0.001",
        "category": "data",
    },
    "https://blockrun.ai/api/v1/pm/polymarket/events": {
        "name": "BlockRun Polymarket",
        "method": "GET",
        "example_url": "https://blockrun.ai/api/v1/pm/polymarket/events?limit=5",
        "price": "$0.001",
        "category": "prediction-markets",
    },
    "https://stableenrich.dev/api/firecrawl/scrape": {
        "name": "Firecrawl (StableEnrich)",
        "method": "POST",
        "example_body": '{"url":"https://example.com"}',
        "example_headers": '{"Content-Type":"application/json"}',
        "price": "$0.013",
        "category": "scraping",
    },
    "https://stableenrich.dev/api/apollo/org-enrich": {
        "name": "Apollo Company Enrichment",
        "method": "POST",
        "example_body": '{"domain":"coinbase.com"}',
        "example_headers": '{"Content-Type":"application/json"}',
        "price": "$0.05",
        "category": "enrichment",
    },
    "https://api.zerion.io/v1/wallets": {
        "name": "Zerion Portfolio",
        "method": "GET",
        "example_url": "https://api.zerion.io/v1/wallets/0x28c6c06298d514db089934071355e5743bf21d60/portfolio",
        "price": "$0.01",
        "category": "defi",
    },
    "https://deepgram.x402.paysponge.com/v1/speak": {
        "name": "Deepgram TTS",
        "method": "POST",
        "example_body": '{"text":"Hello world"}',
        "example_headers": '{"Content-Type":"application/json"}',
        "price": "$0.01",
        "category": "audio",
        "notes": "Add ?model=aura-2-thalia-en to URL for voice selection",
    },
}


def _fetch_json(url: str, timeout: int = 10) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "x402-discovery/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        return {"error": str(e)}


def fetch_bazaar(limit: int = 50) -> list[dict]:
    data = _fetch_json(f"{BAZAAR_URL}?limit={limit}")
    if isinstance(data, dict) and "error" in data:
        print(f"  Bazaar error: {data['error']}", file=sys.stderr)
        return []
    items = data.get("items", []) if isinstance(data, dict) else []
    results = []
    for item in items:
        desc = item.get("description", "")
        url = ""
        method = ""
        bazaar_info = (item.get("extensions", {}).get("bazaar", {}).get("info", {}))
        inp = bazaar_info.get("input", {})
        if inp:
            method = inp.get("method", "POST").upper()
        accepts = item.get("accepts", [])
        price = ""
        for a in accepts:
            if a.get("network", "").startswith("eip155:8453"):
                amt = int(a.get("amount", 0))
                price = f"${amt / 1_000_000:.4f}"
                break
        results.append({
            "source": "bazaar",
            "description": desc[:120],
            "method": method,
            "price": price,
            "networks": [a.get("network", "") for a in accepts],
        })
    return results


def fetch_agentic_market(limit: int = 50) -> list[dict]:
    data = _fetch_json(AGENTIC_URL)
    if isinstance(data, dict) and "error" in data:
        print(f"  agentic.market error: {data['error']}", file=sys.stderr)
        return []
    services = data.get("services", []) if isinstance(data, dict) else []
    results = []
    for svc in services[:limit]:
        for ep in svc.get("endpoints", [])[:3]:
            results.append({
                "source": "agentic.market",
                "name": svc.get("name", ""),
                "url": ep.get("url", ""),
                "method": ep.get("method", "GET"),
                "description": ep.get("description", "")[:120],
                "price": f"${ep.get('pricing', {}).get('amount', '?')}",
                "category": svc.get("category", ""),
            })
    return results


def fetch_x402_list(limit: int = 50) -> list[dict]:
    data = _fetch_json(f"{X402LIST_URL}?limit={limit}")
    if isinstance(data, dict) and "error" in data:
        print(f"  x402-list error: {data['error']}", file=sys.stderr)
        return []
    services = data.get("data", []) if isinstance(data, dict) else []
    results = []
    for svc in services:
        results.append({
            "source": "x402-list",
            "name": svc.get("name", ""),
            "url": svc.get("base_url", ""),
            "description": svc.get("description", "")[:120],
            "price": f"${svc.get('min_price_usd', '?')}",
            "category": svc.get("category", ""),
            "uptime": svc.get("uptime_24h"),
            "response_time_ms": svc.get("avg_response_time_ms"),
            "status": svc.get("status", ""),
        })
    return results


def cmd_search(query: str) -> None:
    query_lower = query.lower()
    print(f"Searching for: {query}\n")

    known_matches = []
    for url, info in KNOWN_ENDPOINTS.items():
        searchable = f"{info['name']} {info.get('category', '')} {url}".lower()
        if query_lower in searchable:
            known_matches.append({"url": url, **info, "source": "verified"})

    if known_matches:
        print("=== VERIFIED ENDPOINTS (tested, working) ===\n")
        for m in known_matches:
            print(f"  {m['name']} ({m['price']})")
            print(f"    {m['method']} {m.get('example_url', m['url'])}")
            if m.get("example_body"):
                print(f"    Body: {m['example_body']}")
            if m.get("notes"):
                print(f"    Note: {m['notes']}")
            print()

    print("=== MARKETPLACE RESULTS ===\n")
    market = fetch_agentic_market(100)
    matches = [e for e in market if query_lower in f"{e.get('name', '')} {e.get('description', '')} {e.get('category', '')} {e.get('url', '')}".lower()]
    if matches:
        for m in matches[:10]:
            print(f"  {m.get('name', '?')} ({m.get('price', '?')})")
            print(f"    {m.get('method', '?')} {m.get('url', '')}")
            print(f"    {m.get('description', '')}")
            print()
    else:
        print("  No marketplace matches.\n")

    print("=== x402-LIST RESULTS ===\n")
    x402list = fetch_x402_list(100)
    matches = [e for e in x402list if query_lower in f"{e.get('name', '')} {e.get('description', '')} {e.get('category', '')}".lower()]
    if matches:
        for m in matches[:10]:
            status = f" [{m.get('status', '')}]" if m.get("status") else ""
            uptime = f" uptime:{m.get('uptime')}%" if m.get("uptime") else ""
            rt = f" {m.get('response_time_ms')}ms" if m.get("response_time_ms") else ""
            print(f"  {m.get('name', '?')} ({m.get('price', '?')}){status}{uptime}{rt}")
            print(f"    {m.get('url', '')}")
            print(f"    {m.get('description', '')}")
            print()
    else:
        print("  No x402-list matches.\n")


def cmd_list(source: str, limit: int) -> None:
    if source == "bazaar":
        results = fetch_bazaar(limit)
    elif source == "agentic-market":
        results = fetch_agentic_market(limit)
    elif source == "x402-list":
        results = fetch_x402_list(limit)
    else:
        print(f"Unknown source: {source}. Use: bazaar, agentic-market, x402-list")
        return

    print(f"=== {source.upper()} ({len(results)} results) ===\n")
    for r in results[:limit]:
        name = r.get("name", r.get("description", "")[:40])
        url = r.get("url", "")
        price = r.get("price", "")
        print(f"  {name} ({price})")
        if url:
            print(f"    {r.get('method', '')} {url}")
        print()


def cmd_test(url: str) -> None:
    print(f"Testing: {url}\n")

    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "x402-discovery/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            headers = dict(resp.headers)
            body = resp.read(500).decode("utf-8", errors="replace")
            latency = int((time.time() - t0) * 1000)

            print(f"  Status: {status}")
            print(f"  Latency: {latency}ms")

            if status == 402:
                pr_header = headers.get("payment-required") or headers.get("PAYMENT-REQUIRED")
                if pr_header:
                    print(f"  x402: YES — endpoint requires payment")
                    try:
                        import base64
                        pr_data = json.loads(base64.b64decode(pr_header))
                        for accept in pr_data.get("accepts", []):
                            amt = int(accept.get("amount", 0))
                            network = accept.get("network", "")
                            print(f"    Price: ${amt / 1_000_000:.6f} USDC on {network}")
                    except Exception:
                        print(f"    Raw header: {pr_header[:100]}")
                else:
                    print("  x402: 402 but no PAYMENT-REQUIRED header")
            else:
                print(f"  Response: {body[:200]}")
                print(f"  Note: endpoint returned {status} without payment — may be free or may need specific request format")

    except urllib.error.HTTPError as e:
        latency = int((time.time() - t0) * 1000)
        if e.code == 402:
            print(f"  Status: 402 Payment Required ({latency}ms)")
            pr_header = e.headers.get("payment-required") or e.headers.get("PAYMENT-REQUIRED")
            if pr_header:
                print(f"  x402: YES — endpoint requires payment")
                try:
                    import base64
                    pr_data = json.loads(base64.b64decode(pr_header))
                    for accept in pr_data.get("accepts", []):
                        amt = int(accept.get("amount", 0))
                        network = accept.get("network", "")
                        scheme = accept.get("scheme", "")
                        print(f"    Price: ${amt / 1_000_000:.6f} USDC on {network} (scheme: {scheme})")
                except Exception:
                    print(f"    Raw header: {pr_header[:200]}")
            print("  HEALTHY — endpoint is live and accepting x402 payments")
        else:
            print(f"  Status: {e.code} ({latency}ms)")
            print(f"  Error: {e.reason}")
    except Exception as e:
        print(f"  FAILED: {e}")


def cmd_howto(url: str) -> None:
    info = KNOWN_ENDPOINTS.get(url)
    if not info:
        for known_url, known_info in KNOWN_ENDPOINTS.items():
            if url in known_url or known_url in url:
                info = known_info
                url = known_url
                break

    if info:
        print(f"=== How to call: {info['name']} ===\n")
        print(f"  Method: {info['method']}")
        print(f"  Price: {info['price']}/call")
        if info.get("notes"):
            print(f"  Note: {info['notes']}")
        print()
        print("  x402_fetch call:")
        if info["method"] == "GET":
            example_url = info.get("example_url", url)
            print(f'    x402_fetch(url="{example_url}", method="GET")')
        else:
            body = info.get("example_body", "{}")
            hdrs = info.get("example_headers", '{"Content-Type":"application/json"}')
            print(f"    x402_fetch(url=\"{url}\", method=\"{info['method']}\", body='{body}', headers={hdrs})")
    else:
        print(f"No verified call instructions for: {url}")
        print("Try: python3 discovery.py test <url> to check if it's a valid x402 endpoint")
        print("Or: python3 discovery.py search <keyword> to find known endpoints")


def cmd_recommend(need: str) -> None:
    print(f"Finding best x402 endpoint for: {need}\n")

    need_lower = need.lower()
    category_map = {
        "search": ["search", "web", "find", "look up", "google"],
        "data": ["price", "crypto", "bitcoin", "ethereum", "market", "defi", "token"],
        "computation": ["calculate", "math", "compute", "wolfram", "science", "convert"],
        "scraping": ["scrape", "crawl", "extract", "website", "page"],
        "enrichment": ["company", "person", "people", "contact", "apollo", "enrich"],
        "prediction-markets": ["prediction", "polymarket", "bet", "forecast"],
        "defi": ["portfolio", "wallet", "balance", "positions", "defi", "zerion"],
        "audio": ["speak", "voice", "tts", "audio", "sound", "speech"],
    }

    matched_category = None
    for cat, keywords in category_map.items():
        if any(kw in need_lower for kw in keywords):
            matched_category = cat
            break

    recommendations = []
    for url, info in KNOWN_ENDPOINTS.items():
        if matched_category and info.get("category") == matched_category:
            recommendations.append({"url": url, **info})
        elif any(word in f"{info['name']} {info.get('category', '')}".lower() for word in need_lower.split()):
            recommendations.append({"url": url, **info})

    if recommendations:
        print(f"=== RECOMMENDED (verified working, category: {matched_category or 'general'}) ===\n")
        for r in recommendations:
            print(f"  ** {r['name']} ** — {r['price']}/call")
            if r["method"] == "GET":
                print(f"    x402_fetch(url=\"{r.get('example_url', r['url'])}\", method=\"GET\")")
            else:
                body = r.get("example_body", "{}")
                print(f"    x402_fetch(url=\"{r['url']}\", method=\"{r['method']}\", body='{body}', headers={{\"Content-Type\":\"application/json\"}})")
            if r.get("notes"):
                print(f"    Note: {r['notes']}")
            print()
    else:
        print("  No verified recommendations found. Searching marketplace...\n")
        cmd_search(need)


def main() -> None:
    parser = argparse.ArgumentParser(description="x402 Discovery Agent")
    sub = parser.add_subparsers(dest="command")

    search_p = sub.add_parser("search", help="Search for x402 endpoints by keyword")
    search_p.add_argument("query", help="Search query")

    list_p = sub.add_parser("list", help="List endpoints from a source")
    list_p.add_argument("--source", default="agentic-market", choices=["bazaar", "agentic-market", "x402-list"])
    list_p.add_argument("--limit", type=int, default=20)

    test_p = sub.add_parser("test", help="Test if a URL is a valid x402 endpoint")
    test_p.add_argument("url", help="URL to test")

    howto_p = sub.add_parser("howto", help="Get exact call instructions for an endpoint")
    howto_p.add_argument("url", help="Endpoint URL")

    recommend_p = sub.add_parser("recommend", help="Get recommendations for a need")
    recommend_p.add_argument("need", help="What you need (e.g. 'web search', 'crypto prices')")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "search":
        cmd_search(args.query)
    elif args.command == "list":
        cmd_list(args.source, args.limit)
    elif args.command == "test":
        cmd_test(args.url)
    elif args.command == "howto":
        cmd_howto(args.url)
    elif args.command == "recommend":
        cmd_recommend(args.need)


if __name__ == "__main__":
    main()
