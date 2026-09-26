'use client'
import { useState, useCallback } from 'react'
import { Panel, FileUpload, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function SpeechToTextPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [language, setLanguage] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const transcribe = useCallback(async () => {
    if (!file) return
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      if (language) form.append('language', language)
      const res = await fetch(`${API_BASE}/audio/stt`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }, body: form })
      const data = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [file, language])

  return (
    <Panel title="Speech to Text" description="Transcribe audio into text using Whisper.">
      <FileUpload accept="audio/*" label="Upload audio" onFile={setFile} />
      <input className="w-full rounded-md border px-3 py-2 text-sm" placeholder="Language (optional, e.g. en, fr, es)" value={language} onChange={(e) => setLanguage(e.target.value)} />
      <ActionButton onClick={transcribe} loading={loading}>Transcribe</ActionButton>
      {result && <ResultBlock label="Result" data={result} />}
    </Panel>
  )
}
