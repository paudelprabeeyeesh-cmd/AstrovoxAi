'use client'
import { useEffect, useState } from 'react'
import { Check, Copy, Play, Loader2, CheckCircle, XCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { CodeBlockExecutor } from './code-block-executor'

interface CodeBlockProps {
  language: string
  code: string
}

type ExecutionStatus = 'idle' | 'running' | 'success' | 'error'

export function CodeBlock({ language, code }: CodeBlockProps) {
  const [html, setHtml] = useState('')
  const [copied, setCopied] = useState(false)
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatus>('idle')
  const [executionOutput, setExecutionOutput] = useState('')
  const [showExecutor, setShowExecutor] = useState(false)
  const [showLineNumbers, setShowLineNumbers] = useState(true)
  const lines = code.split('\n')

  useEffect(() => {
    let cancelled = false
    async function highlight() {
      try {
        const mod = await import('shiki')
        const result = await (mod as any).codeToHtml?.(code, { lang: language, theme: 'github-dark' })
        if (!cancelled) setHtml(result || '')
      } catch {
        if (!cancelled) setHtml('')
      }
    }
    highlight()
    return () => { cancelled = true }
  }, [code, language])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExecute = async () => {
    setShowExecutor(true)
    setExecutionStatus('running')
    setExecutionOutput('')

    try {
      const res = await fetch('/api/code/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, code, timeout: 10 }),
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }

      const data = await res.json()
      const combined = [data.stdout, data.stderr].filter(Boolean).join('\n')
      setExecutionOutput(combined || '(no output)')
      setExecutionStatus(data.return_code === 0 ? 'success' : 'error')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      setExecutionOutput(errorMessage)
      setExecutionStatus('error')
    }
  }

  const getStatusIcon = () => {
    switch (executionStatus) {
      case 'running':
        return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />
      case 'success':
        return <CheckCircle className="h-3.5 w-3.5 text-green-500" />
      case 'error':
        return <XCircle className="h-3.5 w-3.5 text-red-500" />
      default:
        return null
    }
  }

  return (
    <div className="my-4 rounded-lg border border-border bg-muted/30 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-muted/60 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground font-mono">{language}</span>
          {getStatusIcon()}
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLineNumbers(!showLineNumbers)}
            className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
            title={showLineNumbers ? 'Hide line numbers' : 'Show line numbers'}
          >
            <span className="text-xs font-mono">#</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExecute}
            disabled={executionStatus === 'running'}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
            title="Run code"
          >
            {executionStatus === 'running' ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Run
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
            title="Copy code"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        </div>
      </div>

      <div className="flex">
        {showLineNumbers && (
          <div className="select-none border-r border-border bg-muted/30 px-3 py-4 text-right text-xs text-muted-foreground/60 font-mono leading-6">
            {lines.map((_, i) => (
              <div key={i}>{i + 1}</div>
            ))}
          </div>
        )}

        <div
          className="flex-1 overflow-x-auto p-4 [&_pre]:!bg-transparent [&_pre]:!p-0 [&_code]:!text-sm [&_code]:!leading-6"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </div>

      {(showExecutor || executionStatus !== 'idle') && (
        <div className="border-t border-border">
          <button
            onClick={() => setShowExecutor(!showExecutor)}
            className="flex w-full items-center justify-between px-4 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <span className="font-medium">Output</span>
            {showExecutor ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>

          {showExecutor && (
            <div className="border-t border-border bg-black/90 p-3">
              <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-white">
                {executionStatus === 'running' ? (
                  <span className="flex items-center gap-2 text-blue-400">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Running...
                  </span>
                ) : (
                  executionOutput || '(no output)'
                )}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
