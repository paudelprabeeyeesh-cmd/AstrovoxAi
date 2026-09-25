import { supabase } from '../supabase'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function getToken() {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token
}

async function api(path, options = {}) {
  const token = await getToken()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export async function createUniverse(name, physicsRules = {}) {
  return api('/omniscient/sandbox/universes', {
    method: 'POST',
    body: JSON.stringify({ name, physics_rules: physicsRules }),
  })
}

export async function listUniverses() {
  return api('/omniscient/sandbox/universes')
}

export async function runSimulation(universeId, steps = 10) {
  return api(`/omniscient/sandbox/universes/${universeId}/simulate`, {
    method: 'POST',
    body: JSON.stringify({ steps }),
  })
}

export async function destroyUniverse(universeId) {
  return api(`/omniscient/sandbox/universes/${universeId}`, { method: 'DELETE' })
}
