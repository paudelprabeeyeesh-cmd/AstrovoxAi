import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';

export const runtime = 'edge';

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions as any);
  const accessToken = (session?.user as any)?.accessToken || process.env.FASTAPI_TOKEN;

  if (!accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const backendUrl = `${process.env.NEXT_PUBLIC_API_URL}/solve/stream`;

  try {
    const body = await request.text();
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': request.headers.get('content-type') || 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body,
      cache: 'no-store',
    });

    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => 'Upstream error');
      return NextResponse.json({ error: text }, { status: response.status });
    }

    return new Response(response.body, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch (error) {
    return NextResponse.json({ error: 'Proxy failed' }, { status: 502 });
  }
}
