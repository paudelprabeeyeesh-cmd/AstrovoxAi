export const dynamic = 'force-dynamic'

import { NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function proxy(path: string, method: string, body: unknown, searchParams?: URLSearchParams) {
  const url = new URL(path, API_BASE)
  if (searchParams) {
    searchParams.forEach((v, k) => url.searchParams.append(k, v))
  }
  const headers: Record<string, string> = {}
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json'
  }
  const token = typeof globalThis !== 'undefined' ? (globalThis as unknown as { localStorage?: { getItem: (k: string) => string } }).localStorage?.getItem('access_token') : undefined
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(url.toString(), {
    method,
    headers,
    body: method !== 'GET' ? JSON.stringify(body) : undefined,
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

export async function GET() {
  return proxy('/audio/voices', 'GET', undefined)
}

export async function POST(request: Request) {
  const formData = await request.formData()
  const body: Record<string, unknown> = {}
  formData.forEach((value, key) => {
    body[key] = value
  })
  return proxy('/audio/voices/enroll', 'POST', body)
}
