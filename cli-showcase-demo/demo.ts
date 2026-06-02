#!/usr/bin/env npx tsx
/**
 * CLI Showcase Demo — Scripted terminal animation
 * Simulates a Hermes agent with Coinbase wallet doing research + trade via x402
 * 
 * Run: npx tsx cli-showcase-demo/demo.ts
 */

import chalk from 'chalk'

const TYPING_SPEED = 30
const LINE_DELAY = 80
const SECTION_PAUSE = 600
const RESULT_PAUSE = 400

async function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

async function typeText(text: string, speed = TYPING_SPEED): Promise<void> {
  for (const char of text) {
    process.stdout.write(char)
    await sleep(speed)
  }
  process.stdout.write('\n')
}

async function printLine(text: string, delay = LINE_DELAY): Promise<void> {
  console.log(text)
  await sleep(delay)
}

async function printInstant(text: string): Promise<void> {
  console.log(text)
}

const COINBASE_BLUE = chalk.hex('#0052FF')
const GOLD = chalk.hex('#FFD700')
const DIM = chalk.dim
const GREEN = chalk.green
const CYAN = chalk.cyan
const BOLD = chalk.bold

async function banner(): Promise<void> {
  console.clear()
  await printLine('')
  await printLine(COINBASE_BLUE('  ╭──────────────────────────────────────────────────────────────╮'))
  await printLine(COINBASE_BLUE('  │') + BOLD('         ⚕ Hermes Agent × Coinbase for Agents              ') + COINBASE_BLUE('│'))
  await printLine(COINBASE_BLUE('  │') + DIM('         Autonomous research • x402 payments • Base USDC    ') + COINBASE_BLUE('│'))
  await printLine(COINBASE_BLUE('  ├──────────────────────────────────────────────────────────────┤'))
  await printLine(COINBASE_BLUE('  │') + `  ${BOLD('Wallet:')}  ${CYAN('0xb5fa...509B')}  ${GREEN('$47.23 USDC')}  ${DIM('Base')}            ` + COINBASE_BLUE('│'))
  await printLine(COINBASE_BLUE('  │') + `  ${BOLD('Model:')}   qwen3-235b via Venice  ${DIM('(x402)')}                   ` + COINBASE_BLUE('│'))
  await printLine(COINBASE_BLUE('  │') + `  ${BOLD('Skills:')}  ${DIM('research • market-intel • trading')}                   ` + COINBASE_BLUE('│'))
  await printLine(COINBASE_BLUE('  ╰──────────────────────────────────────────────────────────────╯'))
  await printLine('')
}

async function userPrompt(): Promise<void> {
  process.stdout.write(GOLD('  ● '))
  await typeText('Research NVDA earnings using paid data sources and give me a trading recommendation', 25)
  await printLine(DIM('  ────────────────────────────────────────────────────────────────'))
  await sleep(SECTION_PAUSE)
}

async function agentThinking(): Promise<void> {
  await printLine('')
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('Searching agentic.market for financial data providers...')}`)
  await sleep(400)
  await printLine(`  ${DIM('┊')} ${GREEN('✓')} ${DIM('Found:')} ${BOLD('SEC Filings API')} ${DIM('— $0.02/call via x402')}`)
  await sleep(300)
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('x402_fetch → NVDA 10-K + earnings transcript')}  ${GREEN('paid $0.02')}  ${DIM('tx: 0x3c46...bc6a')}`)
  await sleep(400)
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('x402_fetch → financial analysis (OpenRouter)')}  ${GREEN('paid $0.03')}  ${DIM('tx: 0xfd40...3d91')}`)
  await sleep(400)
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('x402_fetch → analyst sentiment (Perplexity)')}  ${GREEN('paid $0.01')}  ${DIM('tx: 0x9493...6ee1')}`)
  await sleep(300)
  await printLine(`  ${DIM('┊')} ${GREEN('✓')} ${DIM('3 services called • Total: $0.06 • 3.8s')}`)
  await sleep(SECTION_PAUSE)
}

async function agentResponse(): Promise<void> {
  await printLine('')
  await printLine(COINBASE_BLUE('  ─  ⚕ Hermes  ───────────────────────────────────────────────────'))
  await printLine('')
  await sleep(RESULT_PAUSE)
  await printLine(BOLD('     NVIDIA (NVDA) — Earnings Analysis'))
  await printLine('')
  await printLine(`     ${BOLD('Revenue:')} $44.1B Q1 FY2026 — 69% YoY growth`)
  await printLine(`     ${BOLD('Data Center:')} $39.2B (+73% YoY) — AI demand accelerating`)
  await printLine(`     ${BOLD('Guidance:')} Q2 revenue $49B ± 2% (above consensus $45.6B)`)
  await printLine(`     ${BOLD('Sentiment:')} 92% bullish — 48/52 analysts rate Overweight`)
  await printLine('')
  await printLine(GREEN('     Recommendation: BUY'))
  await printLine(DIM('     Confidence: High — beat + raise cycle intact, AI capex expanding'))
  await printLine(DIM('     Target: $165 (18% upside from $140)'))
  await printLine('')
  await printLine(`     ${DIM('Cost: $0.06 in x402 micropayments • Time: 3.8 seconds')}`)
  await printLine('')
  await printLine(COINBASE_BLUE('  ─────────────────────────────────────────────────────────────────'))
  await sleep(SECTION_PAUSE)
}

async function tradeExecution(): Promise<void> {
  await printLine('')
  process.stdout.write(GOLD('  ● '))
  await typeText('buy $5,000 of NVDA via Coinbase', 25)
  await printLine(DIM('  ────────────────────────────────────────────────────────────────'))
  await sleep(400)
  await printLine('')
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('coinbase buy --asset NVDA --spend 5000 --payment-method usdc')}`)
  await sleep(600)
  await printLine(`  ${DIM('┊')} ${GREEN('✓')} ${BOLD('Order filled')} — BUY 35.71 NVDA @ $140.00`)
  await printLine(`  ${DIM('┊')}   ${DIM('Order ID: ord_8f2a4c91  •  Settled in USDC on Base  •  Fee: $0.00')}`)
  await sleep(SECTION_PAUSE)
  await printLine('')
  await printLine(COINBASE_BLUE('  ─  ⚕ Hermes  ───────────────────────────────────────────────────'))
  await printLine('')
  await printLine(`     Done. Bought 35.71 shares of NVDA for $5,000 USDC.`)
  await printLine(`     Settled instantly on Base.`)
  await printLine('')
  await printLine(`     ${DIM('Total session cost: $0.06 research + $0.00 trade fee')}`)
  await printLine(`     ${DIM('Wallet balance: $42.17 USDC remaining')}`)
  await printLine('')
  await printLine(COINBASE_BLUE('  ─────────────────────────────────────────────────────────────────'))
  await printLine('')
}

async function main(): Promise<void> {
  await banner()
  await userPrompt()
  await agentThinking()
  await agentResponse()
  await tradeExecution()
}

main().catch(console.error)
