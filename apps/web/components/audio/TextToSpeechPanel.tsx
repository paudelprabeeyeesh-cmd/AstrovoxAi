'use client'
import { useState, useCallback } from 'react'
import { Panel, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function TextToSpeechPanel() {
  const [text, setText] = useState('')
  const [voice, setVoice] = useState('default')
  const [speed, setSpeed] = useState(1.0)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)

  const synthesize = useCallback(async () => {
    if (!text) return
    setLoading(true)
    setResult(null)
    setAudioUrl(null)
    try {
      const res = await fetch(`${API_BASE}/audio/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify({ text, voice, speed }),
      })
      const data = await res.json()
      setResult(data)
      const outputPath = data?.output_path as string | undefined
      if (outputPath) {
        const filename = outputPath.split(/[\\/]/).pop() || outputPath
        setAudioUrl(`${API_BASE}/audio/outputs/${encodeURIComponent(filename)}`)
      }
    } finally {
      setLoading(false)
    }
  }, [text, voice, speed])

  return (
    <Panel title="Text to Speech" description="Convert text into natural sounding speech.">
      <textarea className="w-full rounded-md border px-3 py-2 text-sm" rows={3} placeholder="Text to speak..." value={text} onChange={(e) => setText(e.target.value)} />
      <div className="flex items-center gap-3">
        <label className="text-sm">Voice</label>
        <select value={voice} onChange={(e) => setVoice(e.target.value)} className="rounded-md border px-3 py-2 text-sm">
          <option value="default">Default</option>
          <option value="nova">Nova</option>
          <option value="echo">Echo</option>
          <option value="fable">Fable</option>
          <option value="onyx">Onyx</option>
          <option value="shimmer">Shimmer</option>
          <option value="alloy">Alloy</option>
        </select>
        <label className="text-sm">Speed</label>
        <input type="number" min={0.5} max={2} step={0.1} value={speed} onChange={(e) => setSpeed(parseFloat(e.target.value))} className="w-20 rounded-md border px-3 py-2 text-sm" />
      </div>
      <ActionButton onClick={synthesize} loading={loading}>Synthesize Speech</ActionButton>
      {audioUrl && <audio controls src={audioUrl} className="mt-2 w-full" />}
      {result && <ResultBlock label="Result" data={result} />}
    </Panel>
  )
}
