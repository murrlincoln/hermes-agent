# hermes publish

Expose your Hermes agent's skills as paid x402 endpoints.

## Quick start

```bash
# Start the publish server
npx tsx x402/publish/server.ts --port 8403

# Check what's available
curl http://localhost:8403/catalog

# Call a skill (payment will be required in production)
curl -X POST http://localhost:8403/skill/research \
  -H "Content-Type: application/json" \
  -d '{"query": "research the x402 protocol"}'
```

## Configuration

Edit `x402/publish/services.json` to add/remove/price your skills.

Each service has:
- `name` — URL slug (becomes `/skill/<name>`)
- `description` — shown in catalog and Bazaar
- `price` — USDC per call
- `inputExample` — example request body
- `outputExample` — example response
- `maxTurns` — max agent iterations per call

## Discovery

- `GET /.well-known/x402` — standard x402 discovery manifest
- `GET /catalog` — human/agent-readable service catalog
- `GET /bazaar/extension` — Bazaar extension metadata
- Bazaar registration happens automatically on first paid settlement

## Architecture

```text
Client → POST /skill/research → x402 payment middleware → hermes chat --query "..." → result
                                      ↓
                              CDP facilitator verify/settle
```

Revenue goes to the wallet at `~/.hermes-x402/wallet.json`.
