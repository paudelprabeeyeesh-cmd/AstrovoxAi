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

  const { searchParams } = new URL(request.url)
  const period = searchParams.get('period') || '7d'

  const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/usage/stats?period=${encodeURIComponent(period)}`

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
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
    return NextResponse.json({ error: 'Failed to fetch usage stats' }, { status: 502 })
  }
}
