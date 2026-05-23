# x402 Bundle Catalog

Curated bundles selectable during `x402 init`.

All bundles use:
- `provider: venice`
- `chain: base`
- `spend_asset: USDC`
- Hermes bridge model config patch (`http://127.0.0.1:8402/v1`)

## Available Bundles

| Bundle | Description | Est. cost/hr (USDC) |
|---|---|---:|
| `starter` | Inference-only starter profile (no external paid skills). | 0.05 |
| `research` | Inference + research tools (Exa, Firecrawl, Perplexity, Wolfram). | 0.15 |
| `builder` | Full-stack builder profile (research + sandbox + comms). | 0.25 |
| `web-research` | Search + scraping stack (Exa, Perplexity, StableEnrich Firecrawl proxy, Wolfram). | 0.18 |
| `crypto-intel` | Crypto market intelligence (CoinGecko, BlockRun, Nansen, Zerion, Hyperliquid feeds). | 0.30 |
| `sales-enrichment` | B2B lead generation + enrichment (Apollo, Hunter, Clado email enrich). | 0.38 |
| `social-media` | Social data collection across Reddit/Instagram/TikTok/Facebook. | 0.22 |
| `creative` | Image/video/audio generation (FLUX async, GPT Image, Veo/Sora, Deepgram, advanced Chatterbox). | 0.85 |
| `jobs` | Job search via verified Coresignal endpoint. | 0.12 |
| `travel` | Travel planning + flight tracking + places (Amadeus `originDestinations[]`, Google Maps `textQuery`). | 0.55 |
| `commerce` | Commerce/gifting actions (flowers, gift links, merch, meme search). | 1.45 |

## Notes

- Costs are rough planning estimates and vary by call volume, payload size, and endpoint mix.
- Some endpoints are dynamic-priced and can spike above bundle hourly estimates (notably `commerce` and `creative`).
- Each bundle file includes a `x402_endpoints` section with representative URLs and per-call estimates.
- Broken/unstable endpoints were removed from bundles after test validation (Tavily proxy, twit.sh URL, HireScrape jobs, StableGiftCards, Minerva enrich, etc.).
