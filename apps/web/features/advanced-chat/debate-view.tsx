'use client'
import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ChevronDown, ChevronUp, Users } from 'lucide-react'
import { Perspective } from '@/components/chat/types'

export interface DebateViewProps {
  perspectives: Perspective[]
  synthesis?: string
  onSelectPerspective?: (id: string) => void
}

export function DebateView({ perspectives, synthesis, onSelectPerspective }: DebateViewProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (!perspectives || perspectives.length === 0) {
    return <Card className="p-4 text-sm text-muted-foreground">No perspectives available.</Card>
  }

  return (
    <Card className="flex flex-col">
      <div className="border-b px-4 py-3 flex items-center gap-2">
        <Users className="h-4 w-4" />
        <span className="font-medium text-sm">Multi-Perspective Analysis</span>
        <Badge variant="outline" className="text-xs">
          {perspectives.length} perspectives
        </Badge>
      </div>
      <div className="flex-1 divide-y">
        {perspectives.map((p) => {
          const isExpanded = expanded.has(p.id)
          return (
            <div key={p.id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{p.name}</span>
                  <Badge variant="secondary" className="text-xs">
                    {p.arguments.length} arguments
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggle(p.id)}
                >
                  {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </Button>
              </div>
              {isExpanded && (
                <div className="mt-3 space-y-2">
                  <div>
                    <span className="text-xs font-medium text-muted-foreground">Stance</span>
                    <p className="text-sm mt-1">{p.stance}</p>
                  </div>
                  <div>
                    <span className="text-xs font-medium text-muted-foreground">Arguments</span>
                    <ul className="mt-1 list-disc list-inside text-sm space-y-1">
                      {p.arguments.map((arg, i) => (
                        <li key={i}>{arg}</li>
                      ))}
                    </ul>
                  </div>
                  {p.evidence && p.evidence.length > 0 && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Evidence</span>
                      <ul className="mt-1 list-disc list-inside text-sm space-y-1">
                        {p.evidence.map((ev, i) => (
                          <li key={i}>{ev}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onSelectPerspective?.(p.id)}
                    >
                      Select this perspective
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
      {synthesis && (
        <div className="border-t p-4 bg-muted/30">
          <span className="text-xs font-medium text-muted-foreground">Synthesis</span>
          <p className="text-sm mt-1">{synthesis}</p>
        </div>
      )}
    </Card>
  )
}
