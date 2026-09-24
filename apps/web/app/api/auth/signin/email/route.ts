import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/app/api/auth/[...nextauth]/route'

export const runtime = 'edge'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, password } = body

    if (!email || !password) {
      return NextResponse.json({ message: 'Email and password are required' }, { status: 400 })
    }

    const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/auth/login`

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
      return NextResponse.json({ message: data.message || 'Invalid email or password' }, { status: response.status })
    }

    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ message: 'Something went wrong' }, { status: 500 })
  }
}
