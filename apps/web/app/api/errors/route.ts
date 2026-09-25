import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'edge'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    console.error('[Frontend Error]', {
      message: body.message,
      stack: body.stack,
      name: body.name,
      context: body,
      timestamp: new Date().toISOString(),
    })

    return NextResponse.json({ ok: true })
  } catch {
    return NextResponse.json({ error: 'Failed to log error' }, { status: 500 })
  }
}
