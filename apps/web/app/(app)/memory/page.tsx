'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Trash2, Plus, Sparkles, Loader2 } from 'lucide-react'
import { useMemories } from '@/lib/hooks/use-memory'
import type { MemoryItem } from '@/lib/hooks/use-memory'
import { useToast } from '@/lib/hooks/use-toast'

const CATEGORIES = ['Preference', 'Technical', 'Workflow', 'Context', 'Custom']

const categoryColors: Record<string, string> = {
  Preference: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  Technical: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  Workflow: 'bg-green-500/10 text-green-600 dark:text-green-400',
  Context: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  Custom: 'bg-gray-500/10 text-gray-600 dark:text-gray-400',
}

export default function MemoryPage() {
  const {
    memories,
    loading,
    error,
    categoryFilter,
    setCategoryFilter,
    searchQuery,
    setSearchQuery,
    loadMemories,
    deleteMemory,
    clearAllMemories,
    classifyContent,
  } = useMemories()
  const { toast } = useToast()

  const [isClearDialogOpen, setIsClearDialogOpen] = useState(false)
  const [isClassifyDialogOpen, setIsClassifyDialogOpen] = useState(false)
  const [classifyContent, setClassifyContent] = useState('')
  const [classifyResult, setClassifyResult] = useState<{ category: string; confidence: number; tags: string[]; summary: string } | null>(null)
  const [classifying, setClassifying] = useState(false)

  useEffect(() => {
    loadMemories()
  }, [loadMemories])

  const handleDelete = async (id: string) => {
    await deleteMemory(id)
    toast({ title: 'Memory deleted', description: 'The memory has been removed.' })
  }

  const handleClearAll = async () => {
    await clearAllMemories()
    setIsClearDialogOpen(false)
    toast({ title: 'All memories cleared', description: 'All memories have been removed.' })
  }

  const handleClassify = async () => {
    if (!classifyContent.trim()) return
    setClassifying(true)
    const result = await classifyContent(classifyContent)
    setClassifyResult(result)
    setClassifying(false)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Memory</h1>
          <p className="text-muted-foreground">View and manage what the AI remembers about your preferences.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIsClassifyDialogOpen(true)}>
            <Sparkles className="h-4 w-4 mr-2" />
            Classify
          </Button>
          <Button variant="destructive" onClick={() => setIsClearDialogOpen(true)}>
            <Trash2 className="h-4 w-4 mr-2" />
            Clear All Memory
          </Button>
        </div>
      </div>

      <div className="flex gap-4">
        <div className="flex-1">
          <Input
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <Select value={categoryFilter} onValueChange={setCategoryFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Categories</SelectItem>
            {CATEGORIES.map((cat) => (
              <SelectItem key={cat} value={cat}>{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error && (
        <Card className="p-4 border-destructive/50 bg-destructive/5">
          <p className="text-sm text-destructive">{error.message}</p>
        </Card>
      )}

      <div className="grid gap-4">
        {memories.map((memory: MemoryItem) => (
          <Card key={memory.id} className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-medium">{memory.title}</h3>
                  <span className={'rounded-full px-2 py-0.5 text-xs font-medium ' + (categoryColors[memory.category] || categoryColors.Custom)}>
                    {memory.category}
                  </span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{memory.content}</p>
                <div className="flex items-center gap-2 mt-3">
                  {memory.tags?.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
                  ))}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  Added {new Date(memory.createdAt).toLocaleDateString()}
                </p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => handleDelete(memory.id)} className="ml-4">
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          </Card>
        ))}
        {!loading && memories.length === 0 && (
          <Card className="p-8 text-center">
            <p className="text-muted-foreground">No memories found.</p>
          </Card>
        )}
      </div>

      <Dialog open={isClearDialogOpen} onOpenChange={setIsClearDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear All Memory</DialogTitle>
            <DialogDescription>
              This action will permanently delete all stored memories. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsClearDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleClearAll}>Clear All</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isClassifyDialogOpen} onOpenChange={setIsClassifyDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Classify Memory Content</DialogTitle>
            <DialogDescription>
              Enter content to classify its category and generate tags.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              placeholder="Enter content to classify..."
              value={classifyContent}
              onChange={(e) => setClassifyContent(e.target.value)}
              rows={4}
            />
            {classifyResult && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Category:</span>
                  <Badge variant="default">{classifyResult.category}</Badge>
                  <span className="text-xs text-muted-foreground">({Math.round(classifyResult.confidence * 100)}% confidence)</span>
                </div>
                <p className="text-sm text-muted-foreground">{classifyResult.summary}</p>
                <div className="flex flex-wrap gap-1">
                  {classifyResult.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setIsClassifyDialogOpen(false); setClassifyResult(null); setClassifyContent('') }}>Close</Button>
            <Button onClick={handleClassify} disabled={classifying || !classifyContent.trim()}>
              {classifying && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Classify
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
