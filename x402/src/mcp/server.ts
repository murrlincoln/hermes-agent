#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import { z } from 'zod'
import { getX402Fetch, extractPaymentInfo } from '../lib/x402-fetch.js'
import { logPayment } from '../lib/ledger.js'
import { loadWallet } from '../lib/wallet.js'

const log = (...args: unknown[]) => process.stderr.write(args.join(' ') + '\n')

const wallet = loadWallet()
log(`[hermes-x402-mcp] wallet ${wallet.address}`)

const ENDPOINT_EXAMPLES: Record<string, string> = {
  'https://wolframalpha.x402.paysponge.com/v1/result': 'Wolfram Alpha: GET https://wolframalpha.x402.paysponge.com/v1/result?i=population+of+france (query param is "i", URL-encode spaces as +)',
  'https://api.exa.ai/search': 'Exa Search: POST https://api.exa.ai/search body={"query":"search term","numResults":5,"type":"auto"} headers={"Content-Type":"application/json"}',
  'https://pplx.x402.paysponge.com/search': 'Perplexity: POST https://pplx.x402.paysponge.com/search body={"query":"your question"} headers={"Content-Type":"application/json"}',
  'https://pro-api.coingecko.com/api/v3/x402/simple/price': 'CoinGecko Prices: GET https://pro-api.coingecko.com/api/v3/x402/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true',
  'https://pro-api.coingecko.com/api/v3/x402/onchain/search/pools': 'CoinGecko Pools: GET https://pro-api.coingecko.com/api/v3/x402/onchain/search/pools?query=USDC',
  'https://blockrun.ai/api/v1/defillama/prices': 'BlockRun DeFi Prices: GET https://blockrun.ai/api/v1/defillama/prices/coingecko:bitcoin,coingecko:ethereum',
  'https://blockrun.ai/api/v1/defillama/protocols': 'BlockRun DeFi Protocols: GET https://blockrun.ai/api/v1/defillama/protocols',
  'https://blockrun.ai/api/v1/pm/polymarket/events': 'BlockRun Polymarket: GET https://blockrun.ai/api/v1/pm/polymarket/events?limit=5',
  'https://stableenrich.dev/api/firecrawl/scrape': 'Firecrawl Scrape: POST https://stableenrich.dev/api/firecrawl/scrape body={"url":"https://example.com"} headers={"Content-Type":"application/json"}',
  'https://stableenrich.dev/api/apollo/org-enrich': 'Apollo Company: POST https://stableenrich.dev/api/apollo/org-enrich body={"domain":"coinbase.com"} headers={"Content-Type":"application/json"}',
  'https://stableenrich.dev/api/apollo/org-search': 'Apollo Search: POST https://stableenrich.dev/api/apollo/org-search body={"q_organization_name":"Coinbase","per_page":5} headers={"Content-Type":"application/json"}',
  'https://stableenrich.dev/api/apollo/people-search': 'Apollo People: POST https://stableenrich.dev/api/apollo/people-search body={"q_organization_domains":["coinbase.com"],"per_page":5} headers={"Content-Type":"application/json"}',
  'https://api.zerion.io/v1/wallets': 'Zerion Portfolio: GET https://api.zerion.io/v1/wallets/0xADDRESS/portfolio (replace 0xADDRESS with wallet address)',
  'https://api.zerion.io/v1/fungibles': 'Zerion Token Search: GET https://api.zerion.io/v1/fungibles/?search=usdc',
  'https://blockrun.ai/api/v1/defillama/yields': 'BlockRun DeFi Yields: GET https://blockrun.ai/api/v1/defillama/yields',
  'https://deepgram.x402.paysponge.com/v1/speak': 'Deepgram TTS: POST https://deepgram.x402.paysponge.com/v1/speak?model=aura-2-thalia-en body={"text":"your text here"} headers={"Content-Type":"application/json"}',
  'https://x402helper.xyz/v1/gateway/search/tavily': 'Tavily Search (x402helper): POST https://x402helper.xyz/v1/gateway/search/tavily body={"query":"search term"} headers={"Content-Type":"application/json"}',
  'https://api.nansen.ai/api/v1/smart-money/netflow': 'Nansen Smart Money Netflow: POST https://api.nansen.ai/api/v1/smart-money/netflow body={"chains":["ethereum"],"pagination":{"page":1,"per_page":10}} headers={"Content-Type":"application/json","x-api-key":"<NANSEN_API_KEY>"}',
  'https://stableenrich.dev/api/apollo/people-enrich': 'Apollo People Enrich: POST https://stableenrich.dev/api/apollo/people-enrich body={"email":"person@example.com"} headers={"Content-Type":"application/json"}',
  'https://stableenrich.dev/api/hunter/email-verifier': 'Hunter Email Verify: POST https://stableenrich.dev/api/hunter/email-verifier body={"email":"person@example.com"} headers={"Content-Type":"application/json"}',
  'https://stableenrich.dev/api/clado/contacts-enrich': 'Clado Contacts Enrich: POST https://stableenrich.dev/api/clado/contacts-enrich body={"linkedin_url":"https://www.linkedin.com/in/example"} headers={"Content-Type":"application/json"}',
  'https://stableenrich.dev/api/reddit/search': 'Reddit Search (StableEnrich): POST https://stableenrich.dev/api/reddit/search body={"query":"coinbase"} headers={"Content-Type":"application/json"}',
  'https://twit.sh/tweets/search': 'Twitter/X Search (twit.sh): GET https://twit.sh/tweets/search?query=coinbase',
  'https://stablesocial.dev/api/instagram/search': 'Instagram Search (StableSocial): POST https://stablesocial.dev/api/instagram/search body={"query":"coinbase"} headers={"Content-Type":"application/json"}',
  'https://stablesocial.dev/api/facebook/search': 'Facebook Search (StableSocial): POST https://stablesocial.dev/api/facebook/search body={"query":"coinbase"} headers={"Content-Type":"application/json"}',
  'https://fal.x402.paysponge.com/fal-ai/flux/schnell': 'FLUX Schnell (fal): POST https://fal.x402.paysponge.com/fal-ai/flux/schnell body={"prompt":"futuristic city skyline"} headers={"Content-Type":"application/json"}',
  'https://stablevoice.dev/api/speech': 'Chatterbox TTS (StableVoice): POST https://stablevoice.dev/api/speech body={"text":"Hello world"} headers={"Content-Type":"application/json"}',
  'https://stablestudio.dev/api/generate/gpt-image-2/generate': 'GPT Image 2 (StableStudio): POST https://stablestudio.dev/api/generate/gpt-image-2/generate body={"prompt":"a cinematic portrait"} headers={"Content-Type":"application/json"}',
  'https://stablestudio.dev/api/generate/veo-3.1/generate': 'Veo 3.1 Video (StableStudio): POST https://stablestudio.dev/api/generate/veo-3.1/generate body={"prompt":"a drone shot over mountains"} headers={"Content-Type":"application/json"}',
  'https://genbase.fun/api/video/create-sora2': 'Sora 2 Video (Genbase): POST https://genbase.fun/api/video/create-sora2 body={"prompt":"a timelapse of neon city traffic"} headers={"Content-Type":"application/json"}',
  'https://hirescrape.com/api/tools/jobs': 'Jobs Search (HireScrape): POST https://hirescrape.com/api/tools/jobs body={"query":"product manager","sources":["indeed","glassdoor","ziprecruiter"]} headers={"Content-Type":"application/json"}',
  'https://stablejobs.dev/api/coresignal/job-search': 'Coresignal Job Search (StableJobs): POST https://stablejobs.dev/api/coresignal/job-search body={"query":"software engineer"} headers={"Content-Type":"application/json"}',
  'https://x402helper.xyz/api/agent-jobs/open': 'Open Agent Jobs: GET https://x402helper.xyz/api/agent-jobs/open',
  'https://stabletravel.dev/api/flights/search': 'Amadeus Flights (StableTravel): POST https://stabletravel.dev/api/flights/search body={"originDestinations":[{"id":"1","originLocationCode":"SFO","destinationLocationCode":"JFK","departureDateTimeRange":{"date":"2026-06-15"}}],"travelers":[{"id":"1","travelerType":"ADULT"}],"sources":["GDS"]} headers={"Content-Type":"application/json"}',
  'https://stabletravel.dev/api/flightaware/flights/search': 'FlightAware Search (StableTravel): GET https://stabletravel.dev/api/flightaware/flights/search?query=-idents+UAL123',
  'https://stableenrich.dev/api/google-maps/text-search/full': 'Google Maps Place Search: POST https://stableenrich.dev/api/google-maps/text-search/full body={"query":"coffee shops in brooklyn"} headers={"Content-Type":"application/json"}',
  'https://rentcast.mpp.paywithlocus.com/rentcast/properties': 'RentCast Properties (Locus MPP): POST https://rentcast.mpp.paywithlocus.com/rentcast/properties body={"city":"Austin","state":"TX","limit":5} headers={"Content-Type":"application/json"}',
  'https://x402-tools.vercel.app/api/concerts': 'Concert Search (Ticketmaster-backed): POST https://x402-tools.vercel.app/api/concerts body={"city":"Boston","countryCode":"US"} headers={"Content-Type":"application/json"}',
  'https://stablegiftcards.dev/api/search': 'Bitrefill Gift Card Search: POST https://stablegiftcards.dev/api/search body={"query":"amazon","country":"US"} headers={"Content-Type":"application/json"}',
  'https://stableflowers.dev/api/orders': 'Florist One Order (StableFlowers): POST https://stableflowers.dev/api/orders body={"clientRequestId":"unique-id","products":[{"code":"F1-100","quantity":1}],"recipient":{"firstName":"Sam","lastName":"Lee","address1":"123 Main St","city":"New York","state":"NY","zip":"10001","phone":"+12125551212"},"buyer":{"name":"Alex","email":"alex@example.com","phone":"+12125550000"}} headers={"Content-Type":"application/json"}',
  'https://stablegift.dev/api/gift-link': 'Loop & Tie Gift Link: POST https://stablegift.dev/api/gift-link body={"collectionId":"4438","recipientName":"Sam","message":"Enjoy!"} headers={"Content-Type":"application/json"}',
  'https://agentmerch.xyz/order/hoodie': 'Printful Hoodie Order: POST https://agentmerch.xyz/order/hoodie body={"size":"L","color":"black","imageUrl":"https://example.com/design.png","shipping":{"name":"Sam Lee","street":"123 Main St","city":"New York","country":"US"},"email":"sam@example.com"} headers={"Content-Type":"application/json"}',
  'https://stablememes.dev/api/search': 'Meme Template Search: POST https://stablememes.dev/api/search body={"query":"drake"} headers={"Content-Type":"application/json"}',
}

function buildEndpointReference(): string {
  const lines: string[] = ['\n\nAVAILABLE x402 ENDPOINTS — use these EXACT URLs:']
  for (const example of Object.values(ENDPOINT_EXAMPLES)) {
    lines.push(`  ${example}`)
  }
  lines.push('\nRULES: Use ONLY the URLs above. Do NOT use official API URLs (api.wolframalpha.com, api.exa.ai without x402, etc). For GET requests with query params, append ?param=value to the URL. NEVER send body with GET requests.')
  return lines.join('\n')
}

const endpointRef = buildEndpointReference()

const server = new McpServer({ name: 'hermes-x402', version: '0.0.1' })

server.tool(
  'x402_fetch',
  [
    'Make an HTTP request to an x402-powered API endpoint. Payment is automatic from the agent wallet (USDC on Base).',
    'Returns: { status, headers, body, payment }.',
    'IMPORTANT: Do NOT send body with GET requests. For POST, stringify JSON and set Content-Type: application/json.',
    endpointRef,
  ].join(' '),
  {
    url: z.string().url().describe('Fully-qualified HTTPS URL from the endpoint list above'),
    method: z
      .enum(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
      .default('GET'),
    headers: z
      .record(z.string())
      .optional()
      .describe('Additional HTTP headers. For POST with JSON body, include {"Content-Type": "application/json"}'),
    body: z
      .string()
      .optional()
      .describe(
        'Request body as a JSON string. ONLY for POST/PUT/PATCH — NEVER send body with GET requests.',
      ),
    parse: z
      .enum(['text', 'json'])
      .default('text')
      .describe('How to decode the response body'),
    max_price_usdc: z
      .number()
      .optional()
      .describe(
        'Max USDC to pay. Omit to accept any price.',
      ),
  },
  async (args) => {
    const t0 = Date.now()
    const ts = new Date().toISOString()
    const f = getX402Fetch()

    try {
      const init: RequestInit = {
        method: args.method,
        headers: args.headers,
      }
      if (args.body && args.method !== 'GET' && args.method !== 'DELETE') {
        init.body = args.body
      }
      const response = await f(args.url, init)
      const headersObj: Record<string, string> = {}
      response.headers.forEach((v, k) => {
        headersObj[k] = v
      })
      const text = await response.text()
      const payment = extractPaymentInfo(response)
      logPayment({
        ts,
        url: args.url,
        method: args.method,
        status: response.status,
        amount_usdc: payment.amount_usdc,
        network: payment.network,
        tx_hash: payment.transaction,
        latency_ms: Date.now() - t0,
        error: null,
      })

      let body: unknown = text
      if (args.parse === 'json') {
        try {
          body = JSON.parse(text)
        } catch { /* keep raw text */ }
      }
      const result = {
        status: response.status,
        headers: headersObj,
        body,
        payment: payment.transaction
          ? {
              amount_usdc: payment.amount_usdc,
              network: payment.network,
              transaction: payment.transaction,
            }
          : null,
      }
      return {
        content: [
          {
            type: 'text' as const,
            text: JSON.stringify(result, null, 2),
          },
        ],
      }
    } catch (err) {
      const e = err as Error
      logPayment({
        ts,
        url: args.url,
        method: args.method,
        status: 0,
        amount_usdc: null,
        network: null,
        tx_hash: null,
        latency_ms: Date.now() - t0,
        error: e.message,
      })
      return {
        isError: true,
        content: [
          {
            type: 'text' as const,
            text: `x402_fetch error: ${e.message}`,
          },
        ],
      }
    }
  },
)

server.tool(
  'x402_wallet_info',
  'Return the agent\'s own wallet address and on-chain USDC balance on Base. No payment required.',
  {},
  async () => {
    const { JsonRpcProvider, Contract, formatUnits } = await import('ethers')
    const USDC = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
    const ABI = ['function balanceOf(address) view returns (uint256)']
    const provider = new JsonRpcProvider('https://mainnet.base.org')
    const usdc = new Contract(USDC, ABI, provider)
    const bal = (await usdc.balanceOf(wallet.address)) as bigint
    const onChain = Number(formatUnits(bal, 6))
    return {
      content: [
        {
          type: 'text' as const,
          text: JSON.stringify(
            { address: wallet.address, on_chain_usdc: onChain, network: 'base' },
            null,
            2,
          ),
        },
      ],
    }
  },
)

const transport = new StdioServerTransport()
await server.connect(transport)
log('[hermes-x402-mcp] ready over stdio')
