'use client'
import { ToolCall } from './types'
import { CheckCircle2, XCircle, Loader2, ChevronDown, ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'

interface ToolVisualizationProps {
  tools: ToolCall[]
}

export function ToolVisualization({ tools }: ToolVisualizationProps) {
  const [expanded, setExpanded] = useState(false)

  const getStatusIcon = (status: ToolCall['status']) => {
    switch (status) {
      case 'running':
        return <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-500" />
      case 'completed':
        return <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
      case 'failed':
        return <XCircle className="h-3.5 w-3.5 text-red-500" />
      default:
        return null
    }
  }

  return (
    <div className="rounded-lg border border-border bg-muted/30 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
      >
        <span className="flex items-center gap-2">
          <span>Tools</span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-[10px]">{tools.length}</span>
        </span>
        {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>

      {expanded && (
        <div className="border-t border-border">
          {tools.map((tool) => (
            <div key={tool.id} className="border-b border-border last:border-b-0">
              <div className="flex items-center gap-2 px-4 py-2">
                {getStatusIcon(tool.status)}
                <span className="text-xs font-medium">{tool.name}</span>
                <span className="text-[10px] text-muted-foreground capitalize">{tool.status}</span>
              </div>

              {(tool.arguments || tool.result) && (
                <div className="border-t border-border bg-black/90 p-3">
                  {tool.arguments && (
                    <div className="mb-2">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Input
                      </span>
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-white">
                        {JSON.stringify(tool.arguments, null, 2)}
                      </pre>
                    </div>
                  )}
                  {tool.result && (
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Output
                      </span>
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap font-mono text-xs leading-relaxed text-white">
                        {typeof tool.result === 'string' ? tool.result : JSON.stringify(tool.result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
