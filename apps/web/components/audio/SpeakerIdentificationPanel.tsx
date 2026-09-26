'use client'
import { useState, useCallback } from 'react'
import { Panel, FileUpload, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function SpeakerIdentificationPanel() {
  const [enrollFiles, setEnrollFiles] = useState<File[]>([])
  const [speakerId, setSpeakerId] = useState('')
  const [identifyFile, setIdentifyFile] = useState<File | null>(null)
  const [threshold, setThreshold] = useState(0.7)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [speakers, setSpeakers] = useState<Record<string, unknown>[]>([])

  const loadSpeakers = useCallback(async () => {
    const res = await fetch(`${API_BASE}/audio/speakers`, { headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` } })
    if (res.ok) setSpeakers(await res.json())
  }, [])

  const enroll = useCallback(async () => {
    if (!enrollFiles.length) return
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      enrollFiles.forEach((f) => form.append('files', f))
      form.append('speaker_id', speakerId || 'unknown')
      const res = await fetch(`${API_BASE}/audio/speakers/enroll`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }, body: form })
      const data = await res.json()
      setResult(data)
      loadSpeakers()
    } finally {
      setLoading(false)
    }
  }, [enrollFiles, speakerId, loadSpeakers])

  const identify = useCallback(async () => {
    if (!identifyFile) return
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', identifyFile)
      form.append('threshold', String(threshold))
      const res = await fetch(`${API_BASE}/audio/speakers/identify`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }, body: form })
      const data = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [identifyFile, threshold])

  return (
    <Panel title="Speaker Identification" description="Enroll speakers and identify who is speaking in an audio clip.">
      <FileUpload accept="audio/*" label="Enrollment samples" onFile={(f) => setEnrollFiles((p) => [...p, f])} />
      <input className="w-full rounded-md border px-3 py-2 text-sm" placeholder="Speaker ID" value={speakerId} onChange={(e) => setSpeakerId(e.target.value)} />
      <div className="flex gap-2">
        <ActionButton onClick={enroll} loading={loading}>Enroll Speaker</ActionButton>
        <ActionButton onClick={loadSpeakers} loading={false} variant="secondary">Refresh Speakers</ActionButton>
      </div>
      <FileUpload accept="audio/*" label="Audio to identify" onFile={setIdentifyFile} />
      <div className="flex items-center gap-3">
        <label className="text-sm">Threshold</label>
        <input type="range" min={0} max={1} step={0.05} value={threshold} onChange={(e) => setThreshold(parseFloat(e.target.value))} />
        <span className="text-xs text-muted-foreground">{threshold}</span>
      </div>
      <ActionButton onClick={identify} loading={loading} variant="secondary">Identify Speaker</ActionButton>
      {result && <ResultBlock label="Result" data={result} />}
      {speakers.length > 0 && <ResultBlock label="Enrolled Speakers" data={speakers} />}
    </Panel>
  )
}
