import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'edge'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { name, email, password } = body

    if (!name || !email || !password) {
      return NextResponse.json({ message: 'Name, email, and password are required' }, { status: 400 })
    }

    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/auth/register`

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      return NextResponse.json({ message: data.message || 'Something went wrong' }, { status: response.status })
    }

    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ message: 'Something went wrong' }, { status: 500 })
  }
}
