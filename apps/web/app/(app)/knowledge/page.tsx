'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Loader2, Plus, Network, GitBranch } from 'lucide-react'
import { useKnowledge } from '@/lib/hooks/use-knowledge'

const ENTITY_TYPES = ['Person', 'Organization', 'Concept', 'Technology', 'Document', 'Event']
const RELATIONSHIP_TYPES = ['RELATED_TO', 'PART_OF', 'CONTAINS', 'CREATED_BY', 'REFERENCES', 'BELONGS_TO']

export default function KnowledgePage() {
  const {
    graph,
    loading,
    error,
    loadGraph,
    addEntity,
    addRelationship,
  } = useKnowledge()

  const [isEntityDialogOpen, setIsEntityDialogOpen] = useState(false)
  const [isRelDialogOpen, setIsRelDialogOpen] = useState(false)
  const [entityName, setEntityName] = useState('')
  const [entityType, setEntityType] = useState('Concept')
  const [entityProperties, setEntityProperties] = useState('')
  const [sourceId, setSourceId] = useState('')
  const [targetId, setTargetId] = useState('')
  const [relType, setRelType] = useState('RELATED_TO')
  const [relProperties, setRelProperties] = useState('')

  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  const handleAddEntity = async () => {
    if (!entityName.trim()) return
    let props: Record<string, unknown> = {}
    try {
      props = entityProperties ? JSON.parse(entityProperties) : {}
    } catch {
      props = { raw: entityProperties }
    }
    await addEntity({ name: entityName, type: entityType, properties: props })
    setIsEntityDialogOpen(false)
    setEntityName('')
    setEntityType('Concept')
    setEntityProperties('')
  }

  const handleAddRelationship = async () => {
    if (!sourceId.trim() || !targetId.trim()) return
    let props: Record<string, unknown> = {}
    try {
      props = relProperties ? JSON.parse(relProperties) : {}
    } catch {
      props = { raw: relProperties }
    }
    await addRelationship({ sourceId, targetId, type: relType, properties: props })
    setIsRelDialogOpen(false)
    setSourceId('')
    setTargetId('')
    setRelType('RELATED_TO')
    setRelProperties('')
  }

  const entityById = graph ? Object.fromEntries(graph.entities.map((e) => [e.id, e])) : {}

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Graph</h1>
          <p className="text-muted-foreground">Explore entities and their relationships in your knowledge base.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIsEntityDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Entity
          </Button>
          <Button variant="outline" onClick={() => setIsRelDialogOpen(true)}>
            <GitBranch className="h-4 w-4 mr-2" />
            Add Relationship
          </Button>
        </div>
      </div>

      {error && (
        <Card className="p-4 border-destructive/50 bg-destructive/5">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      )}

      {loading && (
        <div className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && graph && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Network className="h-5 w-5 text-primary" />
                <h2 className="text-lg font-semibold">Graph Visualization</h2>
              </div>
              <div className="relative min-h-[400px] bg-muted/20 rounded-lg border border-dashed border-muted-foreground/30 overflow-hidden">
                <div className="absolute inset-0 p-4">
                  {graph.entities.map((entity, index) => {
                    const col = index % 4
                    const row = Math.floor(index / 4)
                    const left = 10 + col * 22
                    const top = 10 + row * 25
                    return (
                      <div
                        key={entity.id}
                        className="absolute"
                        style={{ left: `${left}%`, top: `${top}%` }}
                      >
                        <div className="relative">
                          <div className="w-16 h-16 rounded-full bg-primary/10 border-2 border-primary flex items-center justify-center">
                            <span className="text-xs font-medium text-center leading-tight px-1">{entity.name}</span>
                          </div>
                          <Badge variant="secondary" className="absolute -bottom-1 left-1/2 -translate-x-1/2 text-[10px] whitespace-nowrap">
                            {entity.type}
                          </Badge>
                        </div>
                      </div>
                    )
                  })}
                  {graph.relationships.map((rel) => {
                    const source = entityById[rel.sourceId]
                    const target = entityById[rel.targetId]
                    if (!source || !target) return null
                    return (
                      <svg key={rel.id} className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
                        <line x1="0" y1="0" x2="0" y2="0" stroke="currentColor" strokeWidth="1" className="text-muted-foreground/40" />
                      </svg>
                    )
                  })}
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="p-4">
              <h3 className="font-semibold mb-3">Entities ({graph.entities.length})</h3>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {graph.entities.map((entity) => (
                  <div key={entity.id} className="flex items-center justify-between p-2 rounded-md bg-muted/30 hover:bg-muted/50 transition-colors">
                    <div>
                      <p className="text-sm font-medium">{entity.name}</p>
                      <p className="text-xs text-muted-foreground">{entity.type}</p>
                    </div>
                  </div>
                ))}
                {graph.entities.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">No entities yet.</p>
                )}
              </div>
            </Card>

            <Card className="p-4">
              <h3 className="font-semibold mb-3">Relationships ({graph.relationships.length})</h3>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {graph.relationships.map((rel) => {
                  const source = entityById[rel.sourceId]
                  const target = entityById[rel.targetId]
                  return (
                    <div key={rel.id} className="p-2 rounded-md bg-muted/30 text-xs">
                      <span className="font-medium">{source?.name || rel.sourceId}</span>
                      <span className="text-muted-foreground mx-1">→</span>
                      <Badge variant="outline" className="text-[10px]">{rel.type}</Badge>
                      <span className="text-muted-foreground mx-1">→</span>
                      <span className="font-medium">{target?.name || rel.targetId}</span>
                    </div>
                  )
                })}
                {graph.relationships.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-4">No relationships yet.</p>
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      <Dialog open={isEntityDialogOpen} onOpenChange={setIsEntityDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Entity</DialogTitle>
            <DialogDescription>Add a new entity to the knowledge graph.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input placeholder="Entity name" value={entityName} onChange={(e) => setEntityName(e.target.value)} />
            <Select value={entityType} onValueChange={setEntityType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ENTITY_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>{type}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Textarea placeholder='Properties (JSON, optional)' value={entityProperties} onChange={(e) => setEntityProperties(e.target.value)} rows={3} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEntityDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddEntity} disabled={!entityName.trim()}>Add Entity</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isRelDialogOpen} onOpenChange={setIsRelDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Relationship</DialogTitle>
            <DialogDescription>Create a relationship between two entities.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Input placeholder="Source entity ID" value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
            <Input placeholder="Target entity ID" value={targetId} onChange={(e) => setTargetId(e.target.value)} />
            <Select value={relType} onValueChange={setRelType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RELATIONSHIP_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>{type}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Textarea placeholder='Properties (JSON, optional)' value={relProperties} onChange={(e) => setRelProperties(e.target.value)} rows={3} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsRelDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAddRelationship} disabled={!sourceId.trim() || !targetId.trim()}>Add Relationship</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
