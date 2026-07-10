// Tiny persistence layer for demo regulatory updates.
//
// Uses Upstash Redis (REST) when UPSTASH_REDIS_REST_URL / _TOKEN are set
// (recommended for Vercel). Falls back to a process-memory array so the app
// also runs with plain `next dev` and no external store. The memory fallback
// resets on cold start — publish a couple entries before the demo.

export interface Update {
  id: string
  title: string
  published_at: string
  body: string
}

const REDIS_URL = process.env.UPSTASH_REDIS_REST_URL
const REDIS_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN
const KEY = 'regulatory:updates'

// Module-level fallback store (survives within a warm serverless instance).
const memory: { updates: Update[] } = { updates: [] }

async function redisCommand(command: unknown[]): Promise<unknown> {
  const res = await fetch(REDIS_URL as string, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${REDIS_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(command),
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`Upstash error ${res.status}`)
  const data = (await res.json()) as { result: unknown }
  return data.result
}

export async function listUpdates(): Promise<Update[]> {
  if (!REDIS_URL || !REDIS_TOKEN) {
    return [...memory.updates].sort((a, b) => (a.id < b.id ? 1 : -1))
  }
  try {
    const raw = (await redisCommand(['GET', KEY])) as string | null
    const arr = raw ? (JSON.parse(raw) as Update[]) : []
    return arr.sort((a, b) => (a.id < b.id ? 1 : -1))
  } catch {
    return []
  }
}

export async function clearUpdates(): Promise<void> {
  if (!REDIS_URL || !REDIS_TOKEN) {
    memory.updates = []
    return
  }
  await redisCommand(['DEL', KEY])
}

export async function addUpdate(input: {
  title: string
  body: string
  published_at?: string
}): Promise<Update> {
  const update: Update = {
    id: `${Date.now()}`,
    title: input.title,
    body: input.body,
    published_at: input.published_at || new Date().toISOString().slice(0, 10),
  }

  if (!REDIS_URL || !REDIS_TOKEN) {
    memory.updates.push(update)
    return update
  }

  const current = await listUpdates()
  current.push(update)
  await redisCommand(['SET', KEY, JSON.stringify(current)])
  return update
}
