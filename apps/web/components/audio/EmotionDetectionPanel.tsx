'use client'
import { useState, useCallback } from 'react'
import { Panel, FileUpload, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function EmotionDetectionPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [segmentDuration, setSegmentDuration] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const detect = useCallback(async () => {
    if (!file) return
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('segment_duration', String(segmentDuration))
      const res = await fetch(`${API_BASE}/audio/emotion/detect`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }, body: form })
      const data = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [file, segmentDuration])

  return (
    <Panel title="Emotion Detection" description="Detect emotions from speech in audio recordings.">
      <FileUpload accept="audio/*" label="Upload audio" onFile={setFile} />
      <div className="flex items-center gap-3">
        <label className="text-sm">Segment duration (s)</label>
        <input type="number" min={1} max={30} value={segmentDuration} onChange={(e) => setSegmentDuration(parseInt(e.target.value))} className="w-24 rounded-md border px-3 py-2 text-sm" />
      </div>
      <ActionButton onClick={detect} loading={loading}>Detect Emotion</ActionButton>
      {result && <ResultBlock label="Result" data={result} />}
    </Panel>
  )
}
