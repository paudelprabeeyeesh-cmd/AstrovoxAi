'use client'
import { useState, useCallback } from 'react'
import { Panel, FileUpload, ActionButton, ResultBlock } from './AudioPanel'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function PodcastSummarizationPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [maxLength, setMaxLength] = useState(500)
  const [includeTranscript, setIncludeTranscript] = useState(true)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)

  const summarize = useCallback(async () => {
    if (!file) return
    setLoading(true)
    setResult(null)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('max_summary_length', String(maxLength))
      form.append('include_transcript', String(includeTranscript))
      const res = await fetch(`${API_BASE}/audio/podcast/summarize`, { method: 'POST', headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }, body: form })
      const data = await res.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }, [file, maxLength, includeTranscript])

  return (
    <Panel title="Podcast Summarization" description="Transcribe and summarize podcast audio or video.">
      <FileUpload accept="audio/*,video/*" label="Upload podcast audio" onFile={setFile} />
      <div className="flex items-center gap-3">
        <label className="text-sm">Max summary length</label>
        <input type="number" min={100} max={2000} value={maxLength} onChange={(e) => setMaxLength(parseInt(e.target.value))} className="w-32 rounded-md border px-3 py-2 text-sm" />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={includeTranscript} onChange={(e) => setIncludeTranscript(e.target.checked)} />
          Include transcript
        </label>
      </div>
      <ActionButton onClick={summarize} loading={loading}>Summarize</ActionButton>
      {result && <ResultBlock label="Result" data={result} />}
    </Panel>
  )
}
