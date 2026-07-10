import { NextResponse } from 'next/server'
import { addUpdate, clearUpdates, listUpdates } from '@/lib/store'

export const dynamic = 'force-dynamic'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS })
}

export async function GET() {
  const updates = await listUpdates()
  return NextResponse.json({ updates }, { headers: CORS })
}

export async function POST(req: Request) {
  let payload: { title?: string; body?: string; published_at?: string }
  try {
    payload = await req.json()
  } catch {
    return NextResponse.json({ error: 'invalid json' }, { status: 400, headers: CORS })
  }

  const title = (payload.title ?? '').trim()
  const body = (payload.body ?? '').trim()
  if (!title && !body) {
    return NextResponse.json(
      { error: 'title or body required' },
      { status: 400, headers: CORS },
    )
  }

  const update = await addUpdate({ title, body, published_at: payload.published_at })
  return NextResponse.json({ update }, { status: 201, headers: CORS })
}

export async function DELETE() {
  await clearUpdates()
  return NextResponse.json({ ok: true }, { headers: CORS })
}
