'use client'
import { useState } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export interface ReasoningNode {
  id: string
  label: string
  type: 'root' | 'step' | 'branch' | 'leaf'
  children?: string[]
  status?: 'pending' | 'active' | 'completed' | 'failed'
  confidence?: number
}

interface ReasoningTreeProps {
  nodes: Record<string, ReasoningNode>
  rootId?: string
}

export function ReasoningTree({ nodes, rootId }: ReasoningTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const root = rootId && nodes[rootId] ? rootId : Object.keys(nodes)[0]

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const renderNode = (nodeId: string, depth: number = 0): JSX.Element => {
    const node = nodes[nodeId]
    if (!node) return <></>
    const hasChildren = node.children && node.children.length > 0
    const isExpanded = expanded.has(nodeId)
    const statusColor = {
      pending: 'bg-gray-400',
      active: 'bg-blue-500',
      completed: 'bg-green-500',
      failed: 'bg-red-500',
    }[node.status || 'pending']

    return (
      <div key={nodeId} className="select-none" style={{ marginLeft: depth * 16 }}>
        <div
          className="flex items-center gap-2 rounded-md px-2 py-1 hover:bg-muted cursor-pointer"
          onClick={() => hasChildren && toggle(nodeId)}
        >
          {hasChildren && (
            <span className="text-muted-foreground">
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </span>
          )}
          <span className={`h-2 w-2 rounded-full ${statusColor}`} />
          <span className="text-sm font-medium">{node.label}</span>
          <Badge variant="outline" className="text-xs">
            {node.type}
          </Badge>
          {node.confidence !== undefined && (
            <Badge variant="secondary" className="text-xs">
              {(node.confidence * 100).toFixed(0)}%
            </Badge>
          )}
        </div>
        {isExpanded && hasChildren && node.children!.map((childId) => renderNode(childId, depth + 1))}
      </div>
    )
  }

  if (!root) return <Card className="p-4 text-sm text-muted-foreground">No reasoning data available.</Card>

  return (
    <Card className="p-4">
      <div className="space-y-1">{renderNode(root)}</div>
    </Card>
  )
}
