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

export async function searchOmniscient(query, realityLayers = null, limit = 20) {
  return api('/omniscient/search', {
    method: 'POST',
    body: JSON.stringify({ query, reality_layers: realityLayers, limit }),
  })
}

export async function getSearchHistory(limit = 100) {
  return api(`/omniscient/search/history?limit=${limit}`)
}

export async function createKnowledgeEntity(entity) {
  return api('/omniscient/knowledge/entities', {
    method: 'POST',
    body: JSON.stringify(entity),
  })
}

export async function createKnowledgeRelationship(relationship) {
  return api('/omniscient/knowledge/relationships', {
    method: 'POST',
    body: JSON.stringify(relationship),
  })
}

export async function getKnowledgeStats() {
  return api('/omniscient/knowledge/stats')
}

export async function getOmniscientStats() {
  return api('/omniscient/stats')
}

export async function translateMatrix(data) {
  return api('/omniscient/translation-matrix/translate', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function createRealityBridge(sourceReality, targetReality, bridgeType = 'standard') {
  return api(`/omniscient/translation-matrix/bridges?source_reality=${sourceReality}&target_reality=${targetReality}&bridge_type=${bridgeType}`, {
    method: 'POST',
  })
}

export async function getRealityBridges() {
  return api('/omniscient/translation-matrix/bridges')
}

export async function createDimensionAnchor(dimension, anchorData) {
  return api('/omniscient/translation-matrix/anchors', {
    method: 'POST',
    body: JSON.stringify({ dimension, anchor_data: anchorData }),
  })
}

export async function getDimensionAnchors(dimension = null) {
  const qs = dimension ? `?dimension=${encodeURIComponent(dimension)}` : ''
  return api(`/omniscient/translation-matrix/anchors${qs}`)
}
