'use client'
import { useState, useCallback } from 'react'
import { Play, Loader2, CheckCircle, XCircle, Copy, Terminal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface CodeExecutorProps {
  language?: string
  code: string
  className?: string
  onExecutionStart?: () => void
  onExecutionComplete?: (result: { output: string; exitCode: number; executionTime: number }) => void
  supportedLanguages?: string[]
}

type ExecutionStatus = 'idle' | 'running' | 'success' | 'error'

const DEFAULT_LANGUAGES = ['javascript', 'typescript', 'python', 'rust', 'go', 'java']

export function CodeExecutor({
  language = 'javascript',
  code,
  className,
  onExecutionStart,
  onExecutionComplete,
  supportedLanguages,
}: CodeExecutorProps) {
  const [status, setStatus] = useState<ExecutionStatus>('idle')
  const [output, setOutput] = useState('')
  const [executionTime, setExecutionTime] = useState<number | null>(null)
  const [selectedLanguage, setSelectedLanguage] = useState(language)
  const [copied, setCopied] = useState(false)

  const availableLanguages = supportedLanguages || DEFAULT_LANGUAGES

  const execute = useCallback(async () => {
    setStatus('running')
    setOutput('')
    setExecutionTime(null)
    onExecutionStart?.()

    const startTime = Date.now()

    try {
      const res = await fetch('/api/code/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: selectedLanguage, code, timeout: 15 }),
      })

      const data = await res.json()
      const combined = [data.stdout, data.stderr].filter(Boolean).join('\n')
      const endTime = Date.now()
      const execTime = endTime - startTime

      setOutput(combined || '(no output)')
      setExecutionTime(execTime)
      const exitCode = data.return_code ?? 0
      const finalStatus = exitCode === 0 ? 'success' : 'error'
      setStatus(finalStatus)
      onExecutionComplete?.({ output: combined, exitCode, executionTime: execTime })
    } catch (err) {
      const endTime = Date.now()
      const errorMessage = err instanceof Error ? err.message : String(err)
      setOutput(`Error: ${errorMessage}`)
      setExecutionTime(endTime - startTime)
      setStatus('error')
      onExecutionComplete?.({ output: `Error: ${errorMessage}`, exitCode: 1, executionTime: endTime - startTime })
    }
  }, [selectedLanguage, code, onExecutionStart, onExecutionComplete])

  const handleCopy = useCallback(async () => {
    if (output) {
      await navigator.clipboard.writeText(output)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [output])

  return (
    <div className={cn('my-2 rounded-lg border bg-muted/50 p-3', className)}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-mono text-muted-foreground">{selectedLanguage}</span>
          {status === 'running' && (
            <span className="text-xs text-muted-foreground">Running...</span>
          )}
          {executionTime !== null && status !== 'running' && (
            <span className="text-xs text-muted-foreground">{executionTime}ms</span>
          )}
          {status === 'success' && (
            <Badge variant="secondary" className="text-[10px] gap-1">
              <CheckCircle className="h-3 w-3 text-green-500" />
              Success
            </Badge>
          )}
          {status === 'error' && (
            <Badge variant="destructive" className="text-[10px] gap-1">
              <XCircle className="h-3 w-3" />
              Error
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1">
          {output && status !== 'running' && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleCopy}
              className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
              title="Copy output"
            >
              {copied ? (
                <CheckCircle className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          )}

          <button
            onClick={execute}
            disabled={status === 'running'}
            className={cn(
              'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
              status === 'success' && 'bg-green-500 text-white hover:bg-green-600',
              status === 'error' && 'bg-red-500 text-white hover:bg-red-600',
              status === 'idle' && 'bg-primary text-primary-foreground hover:bg-primary/90',
              status === 'running' && 'bg-blue-500 text-white cursor-wait'
            )}
          >
            {status === 'running' ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : status === 'success' ? (
              <CheckCircle className="h-3 w-3" />
            ) : status === 'error' ? (
              <XCircle className="h-3 w-3" />
            ) : (
              <Play className="h-3 w-3" />
            )}
            {status === 'running' ? 'Running' : 'Run'}
          </button>
        </div>
      </div>

      {output && (
        <div className="mt-2">
          <pre className="rounded-md bg-black/80 p-3 text-xs text-white font-mono overflow-x-auto whitespace-pre-wrap max-h-[300px] overflow-y-auto">
            {output}
          </pre>
        </div>
      )}
    </div>
  )
}
