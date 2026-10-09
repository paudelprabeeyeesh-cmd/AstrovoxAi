'use client'
import { useMemo, useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react'

export interface GraphNode {
  id: string
  label: string
  type?: string
  x?: number
  y?: number
}

export interface GraphEdge {
  source: string
  target: string
  label?: string
  weight?: number
}

interface KnowledgeGraphViewProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  onNodeClick?: (nodeId: string) => void
  width?: number
  height?: number
}

export function KnowledgeGraphView({
  nodes,
  edges,
  onNodeClick,
  width = 800,
  height = 500,
}: KnowledgeGraphViewProps) {
  const [zoom, setZoom] = useState(1)
  const [filter, setFilter] = useState('')

  const filtered = useMemo(() => {
    const term = filter.toLowerCase()
    const matchedNodes = nodes.filter((n) => n.label.toLowerCase().includes(term) || n.id.includes(term))
    const matchedIds = new Set(matchedNodes.map((n) => n.id))
    const matchedEdges = edges.filter((e) => matchedIds.has(e.source) && matchedIds.has(e.target))
    return { nodes: matchedNodes, edges: matchedEdges }
  }, [nodes, edges, filter])

  const layout = useMemo(() => {
    const positions: Record<string, { x: number; y: number }> = {}
    const cx = width / 2
    const cy = height / 2
    const radius = Math.min(width, height) / 2 - 40
    filtered.nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / Math.max(filtered.nodes.length, 1)
      positions[node.id] = { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) }
    })
    return positions
  }, [filtered.nodes, width, height])

  return (
    <Card className="flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 border-b p-3">
        <Input
          placeholder="Filter nodes..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="max-w-xs"
        />
        <div className="flex gap-1">
          <Button variant="outline" size="icon" onClick={() => setZoom((z) => Math.min(3, z + 0.2))}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setZoom((z) => Math.max(0.3, z - 0.2))}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setZoom(1)}>
            <RotateCcw className="h-4 w-4" />
          </Button>
        </div>
        <span className="text-xs text-muted-foreground">{filtered.nodes.length} nodes</span>
      </div>
      <div className="relative flex-1 overflow-hidden bg-muted/30">
        <svg
          width={width}
          height={height}
          style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
          className="mx-auto"
        >
          {filtered.edges.map((edge, i) => {
            const src = layout[edge.source]
            const tgt = layout[edge.target]
            if (!src || !tgt) return null
            return (
              <line
                key={i}
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke="currentColor"
                strokeOpacity={0.3}
                className="text-border"
              />
            )
          })}
          {filtered.nodes.map((node) => {
            const pos = layout[node.id]
            if (!pos) return null
            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                onClick={() => onNodeClick?.(node.id)}
                className="cursor-pointer"
              >
                <circle r={12} className="fill-primary text-primary" />
                <text y={4} textAnchor="middle" className="fill-primary-foreground text-[10px] font-medium">
                  {node.label.slice(0, 2)}
                </text>
                <title>{node.label}</title>
              </g>
            )
          })}
        </svg>
      </div>
      <div className="border-t p-2 flex flex-wrap gap-1">
        {filtered.nodes.slice(0, 10).map((node) => (
          <Badge key={node.id} variant="secondary" className="text-xs">
            {node.label}
          </Badge>
        ))}
        {filtered.nodes.length > 10 && (
          <Badge variant="outline" className="text-xs">
            +{filtered.nodes.length - 10} more
          </Badge>
        )}
      </div>
    </Card>
  )
}
