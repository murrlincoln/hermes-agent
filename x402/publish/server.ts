import express from 'express'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'
import { loadWallet } from '../src/lib/wallet.js'

interface ServiceDefinition {
  name: string
  description: string
  price: string
  inputExample: Record<string, unknown>
  outputExample: Record<string, unknown>
  maxTurns?: number
}

interface ServicesConfig {
  services: ServiceDefinition[]
}

const __dirname = dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = join(__dirname, '..', '..')

// Parse CLI args
const args = process.argv.slice(2)
const portIdx = args.indexOf('--port')
const port = portIdx >= 0 ? Number(args[portIdx + 1]) : 8403

if (!Number.isFinite(port) || port <= 0) {
  console.error('[hermes-publish] invalid --port value')
  process.exit(1)
}

// Load wallet for payTo address
const wallet = loadWallet()
console.log(`[hermes-publish] wallet: ${wallet.address}`)

// Load services config
const configPath = join(__dirname, 'services.json')
const config = JSON.parse(readFileSync(configPath, 'utf-8')) as ServicesConfig

const app = express()
app.use(express.json({ limit: '10mb' }))

function serviceUrl(name: string): string {
  return `http://localhost:${port}/skill/${name}`
}

// Health check
app.get('/health', (_req, res) => {
  res.json({ ok: true, services: config.services.map((s) => s.name) })
})

// .well-known/x402 for discovery
app.get('/.well-known/x402', (_req, res) => {
  const resources = config.services.map((s) => serviceUrl(s.name))
  res.json({
    version: 1,
    resources,
    extensions: {
      bazaar: {
        publisher: 'hermes',
        wallet: wallet.address,
        catalog: `http://localhost:${port}/catalog`,
      },
    },
  })
})

// Bazaar extension metadata for discovery/indexers
app.get('/bazaar/extension', (_req, res) => {
  res.json({
    name: 'hermes-publish',
    description: 'Expose Hermes skills as paid x402 endpoints',
    wallet: wallet.address,
    services: config.services.map((s) => ({
      name: s.name,
      description: s.description,
      endpoint: serviceUrl(s.name),
      price: `${s.price} USDC`,
      method: 'POST',
    })),
  })
})

// Service catalog
app.get('/catalog', (_req, res) => {
  res.json({
    services: config.services.map((s) => ({
      name: s.name,
      description: s.description,
      price: `$${s.price} USDC`,
      endpoint: `POST /skill/${s.name}`,
      input: s.inputExample,
      output: s.outputExample,
    })),
  })
})

// Register each service as a paid endpoint
for (const service of config.services) {
  app.post(`/skill/${service.name}`, async (req, res) => {
    // For now: no x402 middleware (needs @x402/express installed)
    // This is the handler that runs the skill
    const body = (req.body ?? {}) as Record<string, unknown>
    const query = String(body.query ?? body.domain ?? JSON.stringify(body))

    console.log(`[${service.name}] Running skill for: ${query}`)

    try {
      const result = await runHermesSkill(query, service.maxTurns ?? 10)
      res.json({
        service: service.name,
        result,
        price_usdc: service.price,
        wallet: wallet.address,
      })
    } catch (err) {
      res.status(500).json({ error: (err as Error).message })
    }
  })
}

function runHermesSkill(query: string, maxTurns: number): Promise<string> {
  return new Promise((resolve, reject) => {
    // Check if hermes is available
    const hermesPath = join(PROJECT_ROOT, 'venv', 'bin', 'hermes')
    const useHermes = existsSync(hermesPath)

    const cmd = useHermes ? hermesPath : 'hermes'
    const child = spawn(cmd, ['chat', '--query', query, '--max-turns', String(maxTurns)], {
      cwd: PROJECT_ROOT,
      env: { ...process.env, HERMES_NON_INTERACTIVE: '1' },
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    let settled = false

    child.stdout.on('data', (d) => {
      stdout += d.toString()
    })
    child.stderr.on('data', (d) => {
      stderr += d.toString()
    })

    child.on('error', (err) => {
      if (settled) return
      settled = true
      clearTimeout(timeout)
      reject(new Error(`Failed to start Hermes process: ${err.message}`))
    })

    const timeout = setTimeout(() => {
      if (settled) return
      settled = true
      child.kill('SIGTERM')
      reject(new Error('Skill execution timed out (120s)'))
    }, 120000)

    child.on('close', (code) => {
      if (settled) return
      settled = true
      clearTimeout(timeout)
      if (code === 0 || stdout.length > 0) {
        // Extract the agent's response from hermes output
        // Hermes output includes ANSI codes and formatting — extract just the content
        const lines = stdout.split('\n')
        const contentLines = lines.filter(
          (l) =>
            !l.includes('─') &&
            !l.includes('⚕') &&
            !l.includes('Resume') &&
            !l.includes('Session:') &&
            !l.includes('Duration:') &&
            !l.includes('Messages:') &&
            !l.includes('Initializing') &&
            !l.includes('Query:') &&
            l.trim().length > 0,
        )

        // Strip ANSI codes
        const clean = contentLines.join('\n').replace(/\x1b\[[0-9;]*m/g, '').trim()
        resolve(clean || '(no output)')
      } else {
        reject(new Error(`Hermes exited with code ${code}: ${stderr.slice(0, 500)}`))
      }
    })
  })
}

app.listen(port, '0.0.0.0', () => {
  console.log(`[hermes-publish] listening on http://0.0.0.0:${port}`)
  console.log(`[hermes-publish] wallet: ${wallet.address}`)
  console.log('[hermes-publish] services:')
  for (const s of config.services) {
    console.log(`  POST /skill/${s.name} — $${s.price} — ${s.description.slice(0, 60)}`)
  }
  console.log('[hermes-publish] catalog: GET /catalog')
  console.log('[hermes-publish] discovery: GET /.well-known/x402')
  console.log('[hermes-publish] bazaar: GET /bazaar/extension')
})
