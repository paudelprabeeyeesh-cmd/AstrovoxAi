'use client'
import { useState, useCallback } from 'react'
import { Panel, FileUpload, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function NoiseRemovalPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [strength, setStrength] = useState(0.5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const process = useCallback(async () => {
    if (!file) return
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('strength', String(strength))
      const res = await fetch(`${API_BASE}/audio/noise-removal`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }, body: form })
      const data = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [file, strength])

  return (
    <Panel title="Noise Removal" description="Remove background noise from audio recordings.">
      <FileUpload accept="audio/*" label="Upload noisy audio" onFile={setFile} />
      <div className="flex items-center gap-3">
        <label className="text-sm">Strength</label>
        <input type="range" min={0} max={1} step={0.1} value={strength} onChange={(e) => setStrength(parseFloat(e.target.value))} />
        <span className="text-xs text-muted-foreground">{strength}</span>
      </div>
      <ActionButton onClick={process} loading={loading}>Remove Noise</ActionButton>
      {result && <ResultBlock label="Result" data={result} />}
    </Panel>
  )
}
