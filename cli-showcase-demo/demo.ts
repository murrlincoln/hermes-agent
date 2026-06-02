#!/usr/bin/env npx tsx
/**
 * CLI Showcase Demo — Product showcase scripted animation
 * Press ENTER to advance through each user prompt. Agent responses auto-play.
 * Run: cd cli-showcase-demo && npx tsx demo.ts
 */

import chalk from 'chalk'
import { createInterface } from 'readline'

const TYPING_SPEED = 32
const LINE_DELAY = 60
const SECTION_PAUSE = 800
const THINKING_PAUSE = 500
const RESULT_LINE_DELAY = 110

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

function waitForEnter(): Promise<void> {
  return new Promise((resolve) => {
    const rl = createInterface({ input: process.stdin, output: process.stdout })
    process.stdin.setRawMode?.(true)
    process.stdin.resume()
    process.stdin.once('data', () => {
      process.stdin.setRawMode?.(false)
      rl.close()
      resolve()
    })
  })
}

const BRONZE = chalk.hex('#CD7F32')
const AMBER = chalk.hex('#FFBF00')
const GOLD = chalk.hex('#FFD700')
const DIM_GOLD = chalk.hex('#B8860B')
const COINBASE_BLUE = chalk.hex('#0052FF')
const DIM = chalk.dim
const GREEN = chalk.green
const CYAN = chalk.cyan
const BOLD = chalk.bold

function printBannerInstant(): void {
  console.clear()
  const X = chalk.white.bold('×')
  const lines = [
    '',
    BRONZE('    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⡀⠀⣀⣀⠀⢀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀') + '       ' + COINBASE_BLUE('⠀⠀⠀⠀⣀⣤⣶⣿⣿⣿⣿⣿⣿⣶⣤⣀⠀⠀⠀⠀'),
    BRONZE('    ⠀⠀⠀⠀⠀⠀⢀⣠⣴⣾⣿⣿⣇⠸⣿⣿⠇⣸⣿⣿⣷⣦⣄⡀⠀⠀⠀⠀⠀⠀') + '       ' + COINBASE_BLUE('⠀⠀⣠⣾⣿⡿⠋⠁⠀⠀⠀⠀⠀⠈⠙⢿⣿⣷⣄⠀⠀'),
    AMBER('    ⠀⢀⣠⣴⣶⠿⠋⣩⡿⣿⡿⠻⣿⡇⢠⡄⢸⣿⠟⢿⣿⢿⣍⠙⠿⣶⣦⣄⡀⠀') + '       ' + COINBASE_BLUE('⠀⣴⣿⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣦⠀'),
    AMBER('    ⠀⠀⠉⠉⠁⠶⠟⠋⠀⠉⠀⢀⣈⣁⡈⢁⣈⣁⡀⠀⠉⠀⠙⠻⠶⠈⠉⠉⠀⠀') + '  ' + X + '    ' + COINBASE_BLUE('⢸⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀'),
    GOLD('    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣴⣿⡿⠛⢁⡈⠛⢿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀') + '       ' + COINBASE_BLUE('⢸⣿⣿⠀⠀⠀⠀⠀⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀'),
    GOLD('    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠿⣿⣦⣤⣈⠁⢠⣴⣿⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀') + '       ' + COINBASE_BLUE('⢸⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀'),
    AMBER('    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠻⢿⣿⣦⡉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀') + '       ' + COINBASE_BLUE('⠀⠻⣿⣿⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣿⠟⠀'),
    DIM_GOLD('    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢷⣦⣈⠛⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀') + '       ' + COINBASE_BLUE('⠀⠀⠙⢿⣿⣷⣄⠀⠀⠀⠀⠀⠀⣠⣾⣿⡿⠋⠀⠀'),
    DIM_GOLD('    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣴⠦⠈⠙⠿⣦⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀') + '       ' + COINBASE_BLUE('⠀⠀⠀⠀⠉⠛⠿⣿⣿⣿⣿⠿⠛⠉⠀⠀⠀⠀'),
    DIM_GOLD('    ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⠷⠄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀'),
    '',
    `  ${GOLD('Hermes Agent')}  ${X}  ${COINBASE_BLUE('Coinbase for Agents')}`,
    '',
    `  ${BOLD('Wallet:')}  ${CYAN('0xb5fa...509B')}  ${GREEN('$47.23 USDC')}  ${DIM('Base')}`,
    `  ${BOLD('Model:')}   ${DIM('claude-sonnet-4.6 via OpenRouter')} ${DIM('(x402)')}`,
    `  ${BOLD('Skills:')}  ${DIM('research • market-intel • trading')}`,
    '',
    DIM('  ──────────────────────────────────────────────────────────────────────────────'),
    '',
  ]
  console.log(lines.join('\n'))
}

async function agentThinking(): Promise<void> {
  await printLine('')
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('Searching agentic.market for financial data providers...')}`)
  await sleep(800)
  await printLine(`  ${DIM('┊')} ${GREEN('✓')} ${DIM('Found:')} ${BOLD('SEC Filings API')} ${DIM('($0.02/call, x402 on Base)')}`)
  await sleep(THINKING_PAUSE)
  await printLine(`  ${DIM('┊')}`)
  await sleep(300)
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('x402_fetch → NVDA 10-K + earnings transcript')}`)
  await sleep(600)
  await printLine(`  ${DIM('┊')}   ${GREEN('paid $0.02')}  ${DIM('tx: 0x3c46...bc6a  (1.2s)')}`)
  await sleep(THINKING_PAUSE)
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('x402_fetch → financial analysis via OpenRouter')}`)
  await sleep(700)
  await printLine(`  ${DIM('┊')}   ${GREEN('paid $0.03')}  ${DIM('tx: 0xfd40...3d91  (1.8s)')}`)
  await sleep(THINKING_PAUSE)
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('x402_fetch → analyst sentiment via Perplexity')}`)
  await sleep(500)
  await printLine(`  ${DIM('┊')}   ${GREEN('paid $0.01')}  ${DIM('tx: 0x9493...6ee1  (0.8s)')}`)
  await sleep(400)
  await printLine(`  ${DIM('┊')}`)
  await printLine(`  ${DIM('┊')} ${GREEN('✓')} ${DIM('3 services • $0.06 total • 3.8s')}`)
  await sleep(SECTION_PAUSE)
}

async function agentResponse(): Promise<void> {
  await printLine('')
  await printLine(GOLD(' ─  ⚕ Hermes  ─────────────────────────────────────────────────────'))
  await printLine('')
  await sleep(400)
  await printLine(BOLD('     NVIDIA (NVDA) — Earnings Analysis'))
  await sleep(RESULT_LINE_DELAY)
  await printLine('')
  await sleep(RESULT_LINE_DELAY)
  await printLine(`     ${BOLD('Revenue:')} $44.1B Q1 FY2026 — 69% YoY growth`)
  await sleep(RESULT_LINE_DELAY)
  await printLine(`     ${BOLD('Data Center:')} $39.2B (+73% YoY) — AI demand accelerating`)
  await sleep(RESULT_LINE_DELAY)
  await printLine(`     ${BOLD('Guidance:')} Q2 revenue $49B ± 2% (above consensus $45.6B)`)
  await sleep(RESULT_LINE_DELAY)
  await printLine(`     ${BOLD('Sentiment:')} 92% bullish — 48/52 analysts rate Overweight`)
  await sleep(200)
  await printLine('')
  await sleep(RESULT_LINE_DELAY)
  await printLine(GREEN('     Recommendation: BUY'))
  await sleep(RESULT_LINE_DELAY)
  await printLine(DIM('     Confidence: High — beat + raise cycle intact, AI capex expanding'))
  await sleep(RESULT_LINE_DELAY)
  await printLine(DIM('     Target: $165 (18% upside from $140)'))
  await printLine('')
  await sleep(RESULT_LINE_DELAY)
  await printLine(`     ${DIM('Cost: $0.06 in x402 micropayments • 3.8 seconds')}`)
  await printLine('')
  await printLine(GOLD(' ───────────────────────────────────────────────────────────────────'))
  await sleep(SECTION_PAUSE)
}

async function tradeResponse(): Promise<void> {
  await sleep(600)
  await printLine('')
  await printLine(`  ${DIM('┊')} ${CYAN('⚡')} ${DIM('coinbase buy --asset NVDA --spend 5000 --payment-method usdc')}`)
  await sleep(900)
  await printLine(`  ${DIM('┊')} ${GREEN('✓')} ${BOLD('Order filled')} — BUY 35.71 NVDA @ $140.00`)
  await sleep(200)
  await printLine(`  ${DIM('┊')}   ${DIM('Order ID: ord_8f2a4c91  •  Status: filled')}`)
  await sleep(SECTION_PAUSE)
  await printLine('')
  await printLine(GOLD(' ─  ⚕ Hermes  ─────────────────────────────────────────────────────'))
  await printLine('')
  await sleep(300)
  await printLine(`     Done. Bought 35.71 shares of NVDA for $5,000.`)
  await printLine('')
  await sleep(RESULT_LINE_DELAY)
  await printLine(`     ${DIM('Session: $0.06 research + $5,000.00 trade')}`)
  await sleep(RESULT_LINE_DELAY)
  await printLine(`     ${DIM('Wallet: $42.17 USDC remaining')}`)
  await printLine('')
  await printLine(GOLD(' ───────────────────────────────────────────────────────────────────'))
  await printLine('')
}

async function main(): Promise<void> {
  printBannerInstant()

  // First prompt — press enter to start typing
  await waitForEnter()
  process.stdout.write(GOLD('  ● '))
  await typeText('Research NVDA earnings and give me a trading recommendation', 30)

  // Agent does its thing automatically
  await agentThinking()
  await agentResponse()

  // Second prompt — press enter to trigger the trade
  await printLine('')
  await waitForEnter()
  process.stdout.write(GOLD('  ● '))
  await typeText('buy $5,000 of NVDA', 30)

  // Agent executes trade
  await tradeResponse()
}

main().catch(console.error)
