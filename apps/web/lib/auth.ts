import { getServerSession } from 'next-auth';
import { authOptions } from '@/app/api/auth/[...nextauth]/route';

export { authOptions };

export async function getSession() {
  return getServerSession(authOptions as any);
}

export async function signIn(email: string, password: string, action = 'login') {
  const session = await getServerSession(authOptions as any);
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function signOut() {
  const session = await getServerSession(authOptions as any);
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/logout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(session?.user?.accessToken ? { Authorization: `Bearer ${session.user.accessToken}` } : {}),
    },
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function signUp(email: string, password: string, name?: string) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name }),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function refreshToken(refreshToken: string) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken }),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}
