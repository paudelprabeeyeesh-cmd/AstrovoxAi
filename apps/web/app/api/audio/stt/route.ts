export const dynamic = 'force-dynamic'

import { NextResponse } from 'next/server'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function proxy(path: string, method: string, body: unknown) {
  const url = new URL(path, API_BASE)
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

export async function POST(request: Request) {
  const contentType = request.headers.get('content-type') || ''
  if (contentType.includes('multipart/form-data')) {
    const formData = await request.formData()
    const file = formData.get('file') as File | null
    const language = (formData.get('language') as string) || undefined
    if (!file) return NextResponse.json({ error: 'file is required' }, { status: 400 })
    const uploadForm = new FormData()
    uploadForm.append('file', file)
    if (language) uploadForm.append('language', language)
    const url = new URL('/audio/stt', API_BASE)
    const token = typeof globalThis !== 'undefined' ? (globalThis as unknown as { localStorage?: { getItem: (k: string) => string } }).localStorage?.getItem('access_token') : undefined
    const res = await fetch(url.toString(), { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: uploadForm })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  }
  const body = await request.json()
  return proxy('/audio/stt', 'POST', body)
}
