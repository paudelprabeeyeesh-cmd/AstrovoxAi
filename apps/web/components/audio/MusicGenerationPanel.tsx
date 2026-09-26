'use client'
import { useState, useCallback } from 'react'
import { Panel, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function MusicGenerationPanel() {
  const [prompt, setPrompt] = useState('')
  const [duration, setDuration] = useState(30)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const generate = useCallback(async () => {
    if (!prompt) return
    setLoading(true)
    setResult(null)
    try {
      const res = await fetch(`${API_BASE}/audio/music/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify({ prompt, duration }),
      })
      const data = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [prompt, duration])

  return (
    <Panel title="Music Generation" description="Generate music from text prompts.">
      <textarea className="w-full rounded-md border px-3 py-2 text-sm" rows={3} placeholder="Describe the music you want..." value={prompt} onChange={(e) => setPrompt(e.target.value)} />
      <div className="flex items-center gap-3">
        <label className="text-sm">Duration (s)</label>
        <input type="number" min={5} max={300} value={duration} onChange={(e) => setDuration(parseInt(e.target.value))} className="w-24 rounded-md border px-3 py-2 text-sm" />
      </div>
      <ActionButton onClick={generate} loading={loading}>Generate Music</ActionButton>
      {result && <ResultBlock label="Result" data={result} />}
    </Panel>
  )
}
