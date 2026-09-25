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

export async function getCompletionSuggestions(prefix, context = null, interface = 'universal', limit = 10) {
  return api('/omniscient/completion', {
    method: 'POST',
    body: JSON.stringify({ prefix, context, interface, limit }),
  })
}

export async function recordCompletion(prefix, selected, interface = 'universal') {
  return api('/omniscient/completion/record', {
    method: 'POST',
    body: JSON.stringify({ prefix, context: [selected], interface }),
  })
}

export async function predictThought(userId, context) {
  return api('/omniscient/thought/predict', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId, context }),
  })
}

export async function forecastEvent(eventType, context, timeframe = '7d') {
  return api('/omniscient/forecast', {
    method: 'POST',
    body: JSON.stringify({ event_type: eventType, context, timeframe }),
  })
}

export async function getTrendAnalysis(metric, window = '30d') {
  return api(`/omniscient/forecast/trends/${metric}?window=${window}`)
}
