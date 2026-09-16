'use client'
import { useState } from 'react'
import { Play, Loader2, CheckCircle, XCircle } from 'lucide-react'

interface CodeBlockExecutorProps {
  language: string
  code: string
}

type ExecutionStatus = 'idle' | 'running' | 'success' | 'error'

export function CodeBlockExecutor({ language, code }: CodeBlockExecutorProps) {
  const [status, setStatus] = useState<ExecutionStatus>('idle')
  const [output, setOutput] = useState('')

  const execute = async () => {
    setStatus('running')
    setOutput('')
    try {
      const res = await fetch('/api/code/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, code, timeout: 10 }),
      })
      const data = await res.json()
      const combined = [data.stdout, data.stderr].filter(Boolean).join('\n')
      setOutput(combined || '(no output)')
      setStatus(data.return_code === 0 ? 'success' : 'error')
    } catch (err) {
      setOutput(String(err))
      setStatus('error')
    }
  }

  return (
    <div className="my-2 rounded-lg border bg-muted/50 p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-mono text-muted-foreground">{language}</span>
        <button
          onClick={execute}
          disabled={status === 'running'}
          className="flex items-center gap-1.5 rounded-md bg-primary px-2 py-1 text-xs text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {status === 'running' ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : status === 'success' ? (
            <CheckCircle className="h-3 w-3 text-green-500" />
          ) : status === 'error' ? (
            <XCircle className="h-3 w-3 text-red-500" />
          ) : (
            <Play className="h-3 w-3" />
          )}
          Run
        </button>
      </div>
      {output && (
        <pre className="mt-2 rounded-md bg-black/80 p-2 text-xs text-white font-mono overflow-x-auto whitespace-pre-wrap">
          {output}
        </pre>
      )}
    </div>
  )
}
