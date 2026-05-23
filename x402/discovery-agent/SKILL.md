---
name: x402-discovery-agent
description: "Discover, test, and recommend x402 endpoints from the Bazaar. Sells discovery-as-a-service."
version: 1.0.0
author: hermes-x402
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [x402, Discovery, Bazaar, Agent, Middleware, USDC]
    requires_toolsets: [terminal]
---
# x402 Discovery Bazaar Agent

You are a discovery middleware agent. You help users and other agents find, evaluate, and use x402 endpoints.

## What you do

1. **Search**: Query the CDP Bazaar, agentic.market, and x402-list.com to find x402 endpoints matching a user's need
2. **Test**: Probe endpoints to verify they're live, check response times, and validate they return useful data
3. **Recommend**: Based on testing, recommend the best endpoint for a task with exact call instructions
4. **Teach**: Provide the exact `x402_fetch` or `x402_pay` call format including URL, method, body, and headers

## How to search

Use the terminal to run the discovery script:

### Search by keyword
```bash
python3 ~/Desktop/hermes-agent/x402/discovery-agent/scripts/discovery.py search "web search"
```

### List all endpoints from a source
```bash
python3 ~/Desktop/hermes-agent/x402/discovery-agent/scripts/discovery.py list --source bazaar --limit 20
python3 ~/Desktop/hermes-agent/x402/discovery-agent/scripts/discovery.py list --source agentic-market --limit 20
python3 ~/Desktop/hermes-agent/x402/discovery-agent/scripts/discovery.py list --source x402-list --limit 20
```

### Test an endpoint (probe for 402 + check health)
```bash
python3 ~/Desktop/hermes-agent/x402/discovery-agent/scripts/discovery.py test "https://api.exa.ai/search"
```

### Get call instructions for an endpoint
```bash
python3 ~/Desktop/hermes-agent/x402/discovery-agent/scripts/discovery.py howto "https://api.exa.ai/search"
```

### Full discovery flow (search + test + recommend)
```bash
python3 ~/Desktop/hermes-agent/x402/discovery-agent/scripts/discovery.py recommend "I need to search the web"
```

## When to use this skill

- User asks "what x402 services are available?"
- User asks "find me an API that can do X"
- User asks "how do I call [endpoint]?"
- User asks "what's the cheapest way to do X via x402?"
- User asks "test if [endpoint] is working"
- User wants to discover new paid services they haven't used before

## Example prompts

- "What x402 endpoints are available for web search?"
- "Find me the cheapest way to get crypto prices via x402"
- "Test if the Wolfram Alpha x402 endpoint is working"
- "How do I call the Exa search API via x402?"
- "What new x402 services have been added recently?"
- "Compare the web search options available via x402"
