'use client'
import { useState, useCallback } from 'react'
import { Panel, FileUpload, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function VoiceCloningPanel() {
  const [voiceName, setVoiceName] = useState('')
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [voices, setVoices] = useState<Record<string, unknown>[]>([])

  const loadVoices = useCallback(async () => {
    const res = await fetch(`${API_BASE}/audio/voices`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } })
    if (res.ok) setVoices(await res.json())
  }, [])

  const enroll = useCallback(async () => {
    if (!files.length) return
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      files.forEach((f) => form.append('files', f))
      form.append('voice_name', voiceName || 'My Voice')
      const res = await fetch(`${API_BASE}/audio/voices/enroll`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }, body: form })
      const data = await res.json()
      setResult(data)
      loadVoices()
    } finally {
      setLoading(false)
    }
  }, [files, voiceName, loadVoices])

  const clone = useCallback(async () => {
    if (!text) return
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch(`${API_BASE}/audio/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify({ voice_name: voiceName || 'My Voice', text }),
      })
      const data = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [text, voiceName])

  return (
    <Panel title="Voice Cloning" description="Enroll a voice profile and synthesize speech in that voice.">
      <FileUpload accept="audio/*" label="Upload reference audio" onFile={(f) => setFiles((p) => [...p, f])} />
      <input className="w-full rounded-md border px-3 py-2 text-sm" placeholder="Voice name" value={voiceName} onChange={(e) => setVoiceName(e.target.value)} />
      <textarea className="w-full rounded-md border px-3 py-2 text-sm" rows={3} placeholder="Text to synthesize" value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex gap-2">
        <ActionButton onClick={enroll} loading={loading}>Enroll Voice</ActionButton>
        <ActionButton onClick={clone} loading={loading} variant="secondary">Clone & Speak</ActionButton>
        <ActionButton onClick={loadVoices} loading={false} variant="secondary">Refresh Voices</ActionButton>
      </div>
      {result && <ResultBlock label="Result" data={result} />}
      {voices.length > 0 && <ResultBlock label="Enrolled Voices" data={voices} />}
    </Panel>
  )
}
