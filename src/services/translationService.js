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

export async function translateText(text, sourceLanguage, targetLanguage, context = null) {
  return api('/omniscient/translate', {
    method: 'POST',
    body: JSON.stringify({ text, source_language: sourceLanguage, target_language: targetLanguage, context }),
  })
}

export async function getSupportedLanguages() {
  return api('/omniscient/translate/languages')
}
