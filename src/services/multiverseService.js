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

export async function createTimeline(name, description, branchType = 'conversation') {
  return api('/multiverse/timelines', {
    method: 'POST',
    body: JSON.stringify({ name, description, branch_type: branchType }),
  })
}

export async function listTimelines() {
  return api('/multiverse/timelines')
}

export async function getTimeline(timelineId) {
  return api(`/multiverse/timelines/${timelineId}`)
}

export async function forkUniverse(timelineId, name, promptVariant, modelOverride, temperatureOverride, forkPointMessageId) {
  return api('/multiverse/universes/fork', {
    method: 'POST',
    body: JSON.stringify({ timeline_id: timelineId, name, prompt_variant: promptVariant, model_override: modelOverride, temperature_override: temperatureOverride, fork_point_message_id: forkPointMessageId }),
  })
}

export async function sendUniverseMessage(universeId, content, role = 'user', modelUsed) {
  return api('/multiverse/universes/message', {
    method: 'POST',
    body: JSON.stringify({ universe_id: universeId, content, role, model_used: modelUsed }),
  })
}

export async function getUniverseMessages(universeId, limit = 100, offset = 0) {
  return api(`/multiverse/universes/${universeId}/messages?limit=${limit}&offset=${offset}`)
}

export async function runScenario(universeId, scenarioId, variables = {}, iterations = 1, compareAgainst) {
  return api('/multiverse/scenarios/run', {
    method: 'POST',
    body: JSON.stringify({ universe_id: universeId, scenario_id: scenarioId, variables, iterations, compare_against: compareAgainst }),
  })
}

export async function runParallel(universeId, variants) {
  return api('/multiverse/parallel/run', {
    method: 'POST',
    body: JSON.stringify({ universe_id: universeId, variants }),
  })
}

export async function mergeUniverses(sourceId, targetId, strategy = 'prefer_target', conflictResolution) {
  return api('/multiverse/universes/merge', {
    method: 'POST',
    body: JSON.stringify({ source_universe_id: sourceId, target_universe_id: targetId, strategy, conflict_resolution: conflictResolution }),
  })
}

export async function getVisualization(timelineId) {
  return api(`/multiverse/timelines/${timelineId}/visualization`)
}

export async function exportTimeline(timelineId) {
  return api(`/multiverse/timelines/${timelineId}/export`)
}

export async function importTimeline(payload) {
  return api('/multiverse/timelines/import', {
    method: 'POST',
    body: JSON.stringify({ payload }),
  })
}

export async function collapseUniverse(universeId) {
  return api(`/multiverse/universes/${universeId}`, { method: 'DELETE' })
}

export async function debugMetaReality(universeId) {
  return api(`/multiverse/universes/${universeId}/debug`)
}
