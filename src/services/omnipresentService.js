const API_BASE = import.meta.env.VITE_API_URL || '/api'

async function getToken() {
  const { supabase } = await import('../supabase')
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

export async function getAmbientContext() {
  return api('/omnipresent/context')
}

export async function getContextHistory(limit = 50) {
  return api(`/omnipresent/context/history?limit=${limit}`)
}

export async function registerDevice(deviceType, capabilities = []) {
  return api('/omnipresent/devices/register', {
    method: 'POST',
    body: JSON.stringify({ device_type: deviceType, capabilities }),
  })
}

export async function listDevices() {
  return api('/omnipresent/devices')
}

export async function initiateHandoff(sourceDeviceId, targetDeviceId) {
  return api('/omnipresent/handoff', {
    method: 'POST',
    body: JSON.stringify({ source_device_id: sourceDeviceId, target_device_id: targetDeviceId }),
  })
}

export async function getHandoffHistory() {
  return api('/omnipresent/handoff/history')
}

export async function updateSocialPresence(status, nearbyUsers = []) {
  return api('/omnipresent/social/presence', {
    method: 'POST',
    body: JSON.stringify({ status, nearby_users: nearbyUsers }),
  })
}

export async function getSocialPresence() {
  return api('/omnipresent/social/presence')
}

export async function createCollectiveMind(groupId, participants = []) {
  return api('/omnipresent/collective/mind', {
    method: 'POST',
    body: JSON.stringify({ group_id: groupId, participants }),
  })
}

export async function getCollectiveMind(groupId) {
  return api(`/omnipresent/collective/mind/${encodeURIComponent(groupId)}`)
}

export async function recordSensing(deviceId, sensorType, value, unit = '', confidence = 1.0) {
  return api(`/omnipresent/sensing?device_id=${encodeURIComponent(deviceId)}`, {
    method: 'POST',
    body: JSON.stringify({ sensor_type: sensorType, value, unit, confidence }),
  })
}

export async function getSensings(deviceId, count = 50) {
  return api(`/omnipresent/sensing/${encodeURIComponent(deviceId)}?count=${count}`)
}

export async function predictProactiveAction() {
  return api('/omnipresent/assistance/predict')
}

export async function getProactiveActions() {
  return api('/omnipresent/assistance/history')
}

export async function applyEnvironmentalControl(deviceId, controlType, value, unit = '') {
  return api(`/omnipresent/environment/control?device_id=${encodeURIComponent(deviceId)}`, {
    method: 'POST',
    body: JSON.stringify({ control_type: controlType, value, unit }),
  })
}

export async function getEnvironmentalControls(deviceId) {
  return api(`/omnipresent/environment/controls/${encodeURIComponent(deviceId)}`)
}

export async function getTimeContext() {
  return api('/omnipresent/time/context')
}
