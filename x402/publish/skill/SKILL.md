---
name: x402-publish
description: "Publish skills as paid x402 endpoints. Use terminal commands, NOT a tool call."
version: 1.0.0
author: hermes-x402
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [x402, Publish, Monetize, Producer, Agent Commerce, USDC]
    requires_toolsets: [terminal]
---
# Publish Skills as Paid x402 Endpoints

IMPORTANT: This skill uses TERMINAL COMMANDS (run_terminal / terminal_command), NOT a special tool. Do NOT try to call a tool named "x402-publish" — it doesn't exist. Instead, run the bash commands below via the terminal tool.

You can publish any skill or workflow as a paid x402 endpoint. Other agents and humans discover it via the Bazaar and pay USDC to use it.

## When the user asks you to publish

When the user says things like "publish this skill", "monetize this", "make this available for other agents", or "sell this as a service":

### Step 1: Confirm what to publish

Ask the user:
- What skill/workflow to publish (e.g. "research", "market-intel", "company-research")
- What price to charge (suggest based on your tool costs — aim for 5-10x margin)
- A description of what the skill does

### Step 2: Add the service to the config

Run this to add a new service:
```bash
python3 -c "
import json
config_path = '$(echo ~/Desktop/hermes-agent/x402/publish/services.json)'
with open(config_path, 'r') as f:
    config = json.load(f)
config['services'].append({
    'name': '<SKILL_NAME>',
    'description': '<DESCRIPTION>',
    'price': '<PRICE>',
    'inputExample': {'query': '<EXAMPLE_QUERY>'},
    'outputExample': {'result': '...'},
    'maxTurns': 10
})
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print('Added service: <SKILL_NAME> at \$<PRICE>/call')
"
```

Replace `<SKILL_NAME>`, `<DESCRIPTION>`, `<PRICE>`, and `<EXAMPLE_QUERY>` with the actual values.

### Step 3: Start the publish server

```bash
cd ~/Desktop/hermes-agent && npx tsx x402/publish/server.ts --port 8403 &
```

### Step 4: Verify it's running

```bash
curl -s http://localhost:8403/catalog | python3 -m json.tool
```

### Step 5: Confirm to the user

Tell the user:
- Their skill is now live at `POST http://localhost:8403/skill/<name>`
- Price: $<price> USDC per call
- Other agents can discover it at `http://localhost:8403/.well-known/x402`
- Revenue goes to their wallet

## Pre-configured services

These are already set up in `services.json`:

| Service | Price | Description |
|---------|-------|-------------|
| `research` | $0.50 | Deep research via Exa + Perplexity + Firecrawl |
| `market-intel` | $0.10 | Crypto market brief via CoinGecko + BlockRun + Polymarket |
| `company-research` | $1.00 | Company deep dive via Apollo + Exa + Firecrawl |

To start serving all of them:
```bash
cd ~/Desktop/hermes-agent && npx tsx x402/publish/server.ts --port 8403 &
```

## Pricing guidance

When helping users set prices, consider:
- Your tool costs (check with `x402_wallet_info`)
- Aim for 5-10x margin over your input costs
- Research tasks cost ~$0.05 in tools → charge $0.25-0.50
- Market briefs cost ~$0.03 → charge $0.10-0.25
- Company profiles cost ~$0.09 → charge $0.50-1.00

## Checking revenue

```bash
curl -s http://localhost:8403/health
```
