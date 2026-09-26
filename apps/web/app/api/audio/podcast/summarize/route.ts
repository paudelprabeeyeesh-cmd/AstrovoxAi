export const dynamic = 'force-dynamic'

import { NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function proxy(path: string, method: string, body: unknown) {
  const url = new URL(path, API_BASE)
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = typeof globalThis !== 'undefined' ? (globalThis as unknown as { localStorage?: { getItem: (k: string) => string } }).localStorage?.getItem('access_token') : undefined
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: JSON.stringify(body),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

export async function POST(request: Request) {
  const body = await request.json()
  return proxy('/audio/podcast/summarize', 'POST', body)
}
