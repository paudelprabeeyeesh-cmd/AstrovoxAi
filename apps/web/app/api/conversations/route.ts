import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/app/api/auth/[...nextauth]/route'

export const runtime = 'edge'

export async function GET(request: NextRequest) {
  const session = await getServerSession(authOptions as any)
  const sessionUser = (session as any)?.user
  const accessToken = sessionUser?.accessToken || process.env.FASTAPI_TOKEN

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const searchParams = request.nextUrl.searchParams
  const pinned = searchParams.get('pinned')
  const archived = searchParams.get('archived')
  const folder = searchParams.get('folder')
  const limit = searchParams.get('limit') || '50'
  const offset = searchParams.get('offset') || '0'

  const query = new URLSearchParams()
  query.set('limit', limit)
  query.set('offset', offset)
  if (pinned !== null) query.set('pinned', pinned)
  if (archived !== null) query.set('archived', archived)
  if (folder) query.set('folder', folder)

  const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/conversations?${query.toString()}`

  try {
    const response = await fetch(backendUrl, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: 'no-store',
    })

    if (!response.ok) {
      const text = await response.text().catch(() => 'Upstream error')
      return NextResponse.json({ error: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'Proxy failed' }, { status: 502 })
  }
}

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions as any)
  const sessionUser = (session as any)?.user
  const accessToken = sessionUser?.accessToken || process.env.FASTAPI_TOKEN

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  try {
    const body = await request.json()
    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/conversations`

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    })

    if (!response.ok) {
      const text = await response.text().catch(() => 'Upstream error')
      return NextResponse.json({ error: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ error: 'Proxy failed' }, { status: 502 })
  }
}
