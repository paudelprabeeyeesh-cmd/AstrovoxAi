'use client'
import { useState, useCallback } from 'react'
import { ToolCall } from './types'
import { CheckCircle2, XCircle, Loader2, ChevronDown, ChevronRight, AlertTriangle, Clock, Copy, RefreshCw, Play, Pause, Check, Filter, Terminal, Code2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'

interface ToolVisualizationProps {
  tools: ToolCall[]
  onRetry?: (toolId: string) => void
  onStop?: (toolId: string) => void
  onSelect?: (toolId: string) => void
  selectedToolId?: string
}

type ExecutionPhase = 'idle' | 'running' | 'paused' | 'completed' | 'error'
type ToolLogEntry = { id: string; level: 'info' | 'warn' | 'error'; message: string; timestamp: Date }

export function ToolVisualization({
  tools,
  onRetry,
  onStop,
  onSelect,
  selectedToolId,
}: ToolVisualizationProps) {
  const [expanded, setExpanded] = useState(true)
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set())
  const [copiedOutput, setCopiedOutput] = useState<string | null>(null)
  const [logs, setLogs] = useState<ToolLogEntry[]>([])
  const [showLogs, setShowLogs] = useState(false)
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'tree' | 'timeline'>('tree')

  const getStatusIcon = (status: ToolCall['status']) => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />
      case 'completed':
        return <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
      case 'failed':
        return <XCircle className="h-3.5 w-3.5 text-red-500" />
      case 'pending':
        return <Clock className="h-3.5 w-3.5 text-yellow-500" />
      default:
        return null
    }
  }

  const getStatusColor = (status: ToolCall['status']) => {
    switch (status) {
      case 'running':
        return 'text-blue-500'
      case 'completed':
        return 'text-green-500'
      case 'failed':
        return 'text-red-500'
      case 'pending':
        return 'text-yellow-500'
      default:
        return 'text-muted-foreground'
    }
  }

  const getStatusBadgeVariant = (status: ToolCall['status']) => {
    switch (status) {
      case 'running':
        return 'default'
      case 'completed':
        return 'secondary'
      case 'failed':
        return 'destructive'
      case 'pending':
        return 'outline'
      default:
        return 'outline'
    }
  }

  const handleCopyOutput = useCallback(async (content: string, toolId: string) => {
    await navigator.clipboard.writeText(content)
    setCopiedOutput(toolId)
    setTimeout(() => setCopiedOutput(null), 2000)
  }, [])

  const toggleToolSelection = (toolId: string) => {
    setSelectedTools((prev) => {
      const next = new Set(prev)
      if (next.has(toolId)) {
        next.delete(toolId)
      } else {
        next.add(toolId)
      }
      return next
    })
  }

  const handleRetryWithBackoff = useCallback(async (toolId: string) => {
    setLogs((prev) => [...prev, { id: crypto.randomUUID(), level: 'info', message: `Retrying ${toolId} in 2s...`, timestamp: new Date() }])
    await new Promise((resolve) => setTimeout(resolve, 2000))
    onRetry?.(toolId)
  }, [onRetry])

  const filteredTools = filterStatus === 'all' ? tools : tools.filter((t) => t.status === filterStatus)
  const hasAnyResult = tools.some((t) => t.result)
  const hasAnyError = tools.some((t) => t.status === 'failed')
  const runningCount = tools.filter((t) => t.status === 'running').length
  const completedCount = tools.filter((t) => t.status === 'completed').length

  return (
    <div className="rounded-lg border border-border bg-muted/30 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex flex-1 items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          <span className="flex items-center gap-2">
            <span>Tools</span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-mono">{tools.length}</span>
          </span>
          {runningCount > 0 && (
            <Badge variant="default" className="text-[10px] gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              {runningCount} running
            </Badge>
          )}
          {completedCount > 0 && (
            <Badge variant="secondary" className="text-[10px]">
              {completedCount} done
            </Badge>
          )}
          {hasAnyError && (
            <span className="flex items-center gap-1 text-red-500">
              <AlertTriangle className="h-3 w-3" />
              <span className="text-[10px]">Error</span>
            </span>
          )}
          {hasAnyResult && (
            <span className="text-[10px] text-green-500">Results</span>
          )}
        </button>

        <div className="flex items-center gap-1">
          {selectedTools.size > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedTools(new Set())}
              className="h-7 px-2 text-xs"
            >
              Clear selection ({selectedTools.size})
            </Button>
          )}
          {onRetry && hasAnyError && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                tools.filter((t) => t.status === 'failed').forEach((t) => handleRetryWithBackoff(t.id))
              }}
              className="h-7 gap-1.5 px-2 text-xs"
            >
              <RefreshCw className="h-3 w-3" />
              Retry failed
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLogs(!showLogs)}
            className="h-7 gap-1.5 px-2 text-xs"
          >
            <Terminal className="h-3 w-3" />
            {showLogs ? 'Hide logs' : 'Logs'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setViewMode(viewMode === 'tree' ? 'timeline' : 'tree')}
            className="h-7 px-2 text-xs"
          >
            {viewMode === 'tree' ? 'Timeline' : 'Tree'}
          </Button>
        </div>
      </div>

      {showLogs && (
        <div className="border-t border-border bg-black/90">
          <ScrollArea className="h-32">
            <div className="p-3 space-y-1">
              {logs.length === 0 && (
                <p className="text-xs text-muted-foreground">No logs yet</p>
              )}
              {logs.map((log) => (
                <div key={log.id} className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground">[{log.timestamp.toLocaleTimeString()}]</span>
                  <Badge variant={log.level === 'error' ? 'destructive' : log.level === 'warn' ? 'outline' : 'secondary'} className="text-[10px]">
                    {log.level}
                  </Badge>
                  <span className="text-white">{log.message}</span>
                </div>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {expanded && (
        <div className="border-t border-border">
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'tree' | 'timeline')}>
            <TabsList className="h-8 mx-4 mt-2">
              <TabsTrigger value="tree" className="text-[10px] h-6">Tree</TabsTrigger>
              <TabsTrigger value="timeline" className="text-[10px] h-6">Timeline</TabsTrigger>
            </TabsList>
            <TabsContent value={viewMode} className="mt-2">
              <ScrollArea className="h-64">
                {filteredTools.map((tool, index) => (
                  <div
                    key={tool.id}
                    className={cn(
                      'border-b border-border last:border-b-0 transition-colors',
                      selectedToolId === tool.id && 'bg-accent/50',
                      selectedTools.has(tool.id) && 'bg-accent/30'
                    )}
                  >
                    <div className="flex items-center gap-2 px-4 py-2">
                      <input
                        type="checkbox"
                        checked={selectedTools.has(tool.id)}
                        onChange={() => toggleToolSelection(tool.id)}
                        className="h-3.5 w-3.5 rounded border-border"
                      />
                      {getStatusIcon(tool.status)}
                      <span className="flex-1 text-xs font-medium">{tool.name}</span>
                      <Badge variant={getStatusBadgeVariant(tool.status)} className="text-[10px] capitalize">
                        {tool.status}
                      </Badge>
                      {tool.result && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                          onClick={() => handleCopyOutput(
                            typeof tool.result === 'string' ? tool.result : JSON.stringify(tool.result as Record<string, unknown>, null, 2),
                            tool.id
                          )}
                        >
                        {copiedOutput === tool.id ? (
                          <Check className="h-3 w-3 text-green-500" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                        </Button>
                      )}
                      {onRetry && tool.status === 'failed' && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                          onClick={() => handleRetryWithBackoff(tool.id)}
                        >
                          <RefreshCw className="h-3 w-3" />
                        </Button>
                      )}
                    </div>

                    {(tool.arguments || tool.result) && (
                      <div className="border-t border-border bg-black/90">
                        {tool.arguments && (
                          <div className="border-b border-border/50 p-3">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                                Input
                              </span>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-5 w-5 p-0 text-muted-foreground hover:text-foreground"
                                onClick={() => handleCopyOutput(JSON.stringify(tool.arguments, null, 2), `${tool.id}-input`)}
                              >
                                <Copy className="h-3 w-3" />
                              </Button>
                            </div>
                            <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-white">
                              {JSON.stringify(tool.arguments, null, 2)}
                            </pre>
                          </div>
                        )}
                        {tool.result && (
                          <div className="p-3">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                                Output
                              </span>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-5 w-5 p-0 text-muted-foreground hover:text-foreground"
                                onClick={() => handleCopyOutput(
                                  typeof tool.result === 'string' ? tool.result : JSON.stringify(tool.result as Record<string, unknown>, null, 2),
                                  `${tool.id}-output`
                                )}
                              >
                                {copiedOutput === `${tool.id}-output` ? (
                                  <Check className="h-3 w-3 text-green-500" />
                                ) : (
                                  <Copy className="h-3 w-3" />
                                )}
                              </Button>
                            </div>
                            <pre
                              className={cn(
                                'overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed',
                                tool.status === 'failed' ? 'text-red-400' : 'text-white'
                              )}
                            >
                              {typeof tool.result === 'string'
                                ? tool.result
                                 : JSON.stringify(tool.result, null, 2) as string}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  )
}
