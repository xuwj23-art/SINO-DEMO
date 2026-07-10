// ============================================================
// Synthetic transaction stream (ALL FICTIONAL — no real data)
// ============================================================
// Generates a live-looking flow of transactions for the monitoring demo:
//   - Mostly NORMAL small trades/deposits (陈大文/李美玲/张正常), ~15:1 ratio
//   - A scripted SUSPECT burst from 王志強 at ~18s: 3 large deposits from 2
//     third-party accounts within 5 minutes → the "needle in a haystack" visual.
//
// Detection is deterministic on the frontend (rules below); the AI only does
// the risk adjudication afterwards. This keeps the demo reproducible.
// ============================================================

import type { DemoTransaction } from '../api/demo'
import { getClientData } from './demoClients'

export interface StreamEvent {
  txn: DemoTransaction
  suspect: boolean
}

// Chinese labels for the suspect flags (shown to non-technical audience).
export const SUSPECT_LABELS: Record<string, string> = {
  large_frequency: '短时间多笔大额',
  third_party: '第三方账户入金',
  income_mismatch: '金额与收入不符',
  rapid_movement: '快进快出',
}

// --- Normal behavior templates per client -----------------------------------
const NORMAL_CLIENT_IDS = ['SPDEMO001', 'SPDEMO002', 'SPDEMO004']
const NORMAL_TYPES: DemoTransaction['type'][] = ['buy', 'sell', 'deposit', 'withdraw']
const NORMAL_CCY = 'HKD'

function clientName(id: string): string {
  return getClientData(id)?.account.accName as string
}

function rand<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
}

let seq = 0
function nextId(): string {
  seq += 1
  return `TXN${String(Date.now()).slice(-6)}${seq}`
}

// Build a mundane transaction for one of the clean clients.
function makeNormalTxn(time: Date): DemoTransaction {
  const id = rand(NORMAL_CLIENT_IDS)
  const type = rand(NORMAL_TYPES)
  // amounts deliberately small and unremarkable
  const amount =
    type === 'deposit' || type === 'withdraw'
      ? rand([10000, 20000, 30000, 50000, 80000])
      : rand([50000, 100000, 150000, 200000, 300000])
  return {
    id: nextId(),
    time: time.toTimeString().slice(0, 8),
    client_id: id,
    client_name: clientName(id),
    type,
    amount,
    currency: NORMAL_CCY,
    counterparty: type === 'deposit' || type === 'withdraw' ? rand(['恒生銀行', '匯豐銀行', '中銀香港']) : undefined,
  }
}

// The scripted suspect sequence: 王志強 receives 3 large third-party deposits
// in quick succession, each far exceeding his declared income.
function makeSuspectBurst(start: Date): DemoTransaction[] {
  const out: DemoTransaction[] = []
  const counterparties = ['李某輝（第三方）', '張某強（第三方）']
  const amounts = [5000000, 6000000, 4000000] // vs annual_income 300k
  for (let i = 0; i < 3; i++) {
    const t = new Date(start.getTime() + i * 90000) // ~90s apart in story time
    out.push({
      id: nextId(),
      time: t.toTimeString().slice(0, 8),
      client_id: 'SPDEMO003',
      client_name: '王志強',
      type: 'deposit',
      amount: amounts[i],
      currency: 'HKD',
      counterparty: counterparties[i % 2],
      suspect_flags: ['large_frequency', 'third_party', 'income_mismatch'],
    })
  }
  return out
}

// Deterministic suspect rule: a txn is suspect if flagged as such (the scripted
// burst sets suspect_flags). Keeps the stream logic simple and reproducible.
function isSuspect(t: DemoTransaction): boolean {
  return !!t.suspect_flags && t.suspect_flags.length > 0
}

// --- The stream -------------------------------------------------------------
// Emits transactions on a timer. Normal txns every ~1.2-2s; the scripted
// suspect burst fires once around 18s after start. Returns a stop function.
const NORMAL_INTERVAL = () => 1200 + Math.random() * 800 // 1.2-2.0s
const BURST_AT_MS = 18000 // ~18s into the demo

export function startStream(onEvent: (e: StreamEvent) => void): () => void {
  let stopped = false
  const timers: ReturnType<typeof setTimeout>[] = []

  const emitNormal = () => {
    if (stopped) return
    const txn = makeNormalTxn(new Date())
    onEvent({ txn, suspect: isSuspect(txn) })
    const t = setTimeout(emitNormal, NORMAL_INTERVAL())
    timers.push(t)
  }

  // Kick off the normal flow.
  emitNormal()

  // Schedule the scripted suspect burst (fires each txn ~1.5s apart so they
  // visibly "pop" out of the normal stream).
  const burst = makeSuspectBurst(new Date())
  burst.forEach((txn, i) => {
    const t = setTimeout(() => {
      if (stopped) return
      onEvent({ txn, suspect: true })
    }, BURST_AT_MS + i * 1500)
    timers.push(t)
  })

  return () => {
    stopped = true
    timers.forEach((t) => clearTimeout(t))
  }
}
