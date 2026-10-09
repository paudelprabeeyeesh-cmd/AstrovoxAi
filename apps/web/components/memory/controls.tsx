'use client'
import { useState } from 'react'
import { Brain, Trash2, RefreshCw, Eye, EyeOff, Search, Download, Upload, HardDrive, Clock, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'

interface MemoryItem {
  id: string
  type: 'fact' | 'preference' | 'context' | 'conversation'
  content: string
  timestamp: Date
  source?: string
  confidence: number
  visible: boolean
}

const sampleMemory: MemoryItem[] = [
  {
    id: '1',
    type: 'fact',
    content: 'User prefers TypeScript over JavaScript for new projects',
    timestamp: new Date(Date.now() - 86400000),
    source: 'Conversation #42',
    confidence: 0.95,
    visible: true,
  },
  {
    id: '2',
    type: 'preference',
    content: 'Prefers dark mode theme',
    timestamp: new Date(Date.now() - 172800000),
    source: 'Settings',
    confidence: 1.0,
    visible: true,
  },
  {
    id: '3',
    type: 'context',
    content: 'Working on a React Native mobile application with Expo',
    timestamp: new Date(Date.now() - 3600000),
    source: 'Current session',
    confidence: 0.88,
    visible: true,
  },
  {
    id: '4',
    type: 'conversation',
    content: 'Discussed database schema design for multi-tenant SaaS application',
    timestamp: new Date(Date.now() - 604800000),
    source: 'Conversation #38',
    confidence: 0.82,
    visible: true,
  },
  {
    id: '5',
    type: 'fact',
    content: 'User has experience with Node.js, Python, and Rust',
    timestamp: new Date(Date.now() - 1209600000),
    source: 'Conversation #12',
    confidence: 0.9,
    visible: false,
  },
]

const typeConfig = {
  fact: { icon: Brain, color: 'bg-blue-500', label: 'Fact' },
  preference: { icon: Zap, color: 'bg-purple-500', label: 'Preference' },
  context: { icon: Clock, color: 'bg-green-500', label: 'Context' },
  conversation: { icon: HardDrive, color: 'bg-amber-500', label: 'Conversation' },
}

export function MemoryControls() {
  const [memory, setMemory] = useState<MemoryItem[]>(sampleMemory)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>('all')

  const toggleVisibility = (id: string) => {
    setMemory((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, visible: !item.visible } : item
      )
    )
  }

  const deleteMemory = (id: string) => {
    setMemory((prev) => prev.filter((item) => item.id !== id))
  }

  const clearAll = () => {
    setMemory([])
  }

  const filteredMemory = memory.filter((item) => {
    const matchesSearch = !searchQuery || item.content.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = selectedType === 'all' || item.type === selectedType
    return matchesSearch && matchesType
  })

  const formatTimeAgo = (date: Date) => {
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
    if (seconds < 60) return 'Just now'
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    if (days < 7) return `${days}d ago`
    const weeks = Math.floor(days / 7)
    return `${weeks}w ago`
  }

  const visibleCount = memory.filter((m) => m.visible).length
  const totalConfidence = memory.reduce((sum, m) => sum + m.confidence, 0)
  const avgConfidence = memory.length > 0 ? (totalConfidence / memory.length * 100).toFixed(0) : 0

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between pb-4">
        <div>
          <h2 className="text-xl font-semibold">Memory Management</h2>
          <p className="text-sm text-muted-foreground">
            {visibleCount} of {memory.length} items visible
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <Upload className="h-4 w-4" />
            Import
          </Button>
          <Button variant="destructive" size="sm" onClick={clearAll} disabled={memory.length === 0}>
            <Trash2 className="h-4 w-4" />
            Clear All
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 pb-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Memories</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{memory.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg. Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgConfidence}%</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Last Updated</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm font-medium">
              {memory.length > 0 ? formatTimeAgo(memory[0].timestamp) : 'Never'}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-4 pb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        <Tabs value={selectedType} onValueChange={setSelectedType}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="fact">Facts</TabsTrigger>
            <TabsTrigger value="preference">Preferences</TabsTrigger>
            <TabsTrigger value="context">Context</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto">
        {filteredMemory.map((item) => {
          const config = typeConfig[item.type]

          return (
            <Card key={item.id} className={cn(!item.visible && 'opacity-60')}>
              <CardContent className="flex items-start gap-3 p-4">
                <div className={cn('rounded-md p-2', config.color, 'text-white')}>
                  <config.icon className="h-4 w-4" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">
                      {config.label}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatTimeAgo(item.timestamp)}
                    </span>
                    {item.source && (
                      <span className="text-xs text-muted-foreground">from {item.source}</span>
                    )}
                  </div>

                  <p className="mt-1 text-sm">{item.content}</p>

                  <div className="mt-2 flex items-center gap-1">
                    <div className="h-1.5 flex-1 rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full bg-primary"
                        style={{ width: `${item.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-muted-foreground">
                      {Math.round(item.confidence * 100)}%
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => toggleVisibility(item.id)}
                    className="h-7 w-7 p-0"
                  >
                    {item.visible ? (
                      <Eye className="h-3.5 w-3.5" />
                    ) : (
                      <EyeOff className="h-3.5 w-3.5" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteMemory(item.id)}
                    className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}

        {filteredMemory.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Brain className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-2 text-sm font-medium">No memories found</h3>
            <p className="text-sm text-muted-foreground">
              {searchQuery ? 'Try adjusting your search' : 'Memories will appear here as you interact'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
