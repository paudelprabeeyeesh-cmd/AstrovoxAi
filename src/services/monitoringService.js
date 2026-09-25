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

export async function registerMonitor(name, config) {
  return api('/omniscient/monitors', {
    method: 'POST',
    body: JSON.stringify({ name, config }),
  })
}

export async function recordMonitorEvent(source, eventType, severity = 'info', data = {}) {
  return api('/omniscient/monitors/events', {
    method: 'POST',
    body: JSON.stringify({ source, event_type: eventType, severity, data }),
  })
}

export async function getMonitorHealth() {
  return api('/omniscient/monitors/health')
}

export async function getMonitorAlerts(severity = null, limit = 50) {
  const qs = new URLSearchParams()
  if (severity) qs.set('severity', severity)
  qs.set('limit', limit)
  return api(`/omniscient/monitors/alerts?${qs.toString()}`)
}
