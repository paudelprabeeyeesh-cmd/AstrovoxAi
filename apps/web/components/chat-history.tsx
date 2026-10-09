'use client'

import { useState, useCallback, useMemo } from 'react'
import { Message } from '@/lib/types'
import { MessageSquare, Clock, Trash2, MoreHorizontal, Star, Search, Filter } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ChatHistoryProps {
  conversations: Message[]
  activeId?: string
  onSelect?: (id: string) => void
  onDelete?: (id: string) => void
  onRename?: (id: string, title: string) => void
  onNewChat?: () => void
}

type SortOption = 'newest' | 'oldest' | 'title'

export function ChatHistory({
  conversations,
  activeId,
  onSelect,
  onDelete,
  onRename,
  onNewChat,
}: ChatHistoryProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [sortBy, setSortBy] = useState<SortOption>('newest')
  const [filterModel, setFilterModel] = useState<string>('all')
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false)

  const sortedConversations = useMemo(() => {
    let filtered = conversations

    if (searchQuery) {
      filtered = filtered.filter((conv) =>
        conv.content.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    if (filterModel !== 'all') {
      filtered = filtered.filter((conv) => conv.model === filterModel)
    }

    if (showFavoritesOnly) {
      filtered = filtered.filter((conv) => conv.feedback === 'up')
    }

    const sorted = [...filtered]
    switch (sortBy) {
      case 'newest':
        sorted.sort((a, b) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime())
        break
      case 'oldest':
        sorted.sort((a, b) => new Date(a.timestamp || 0).getTime() - new Date(b.timestamp || 0).getTime())
        break
      case 'title':
        sorted.sort((a, b) => a.content.localeCompare(b.content))
        break
    }

    return sorted
  }, [conversations, searchQuery, sortBy, filterModel, showFavoritesOnly])

  const uniqueModels = useMemo(() => {
    const models = new Set(conversations.map((c) => c.model).filter(Boolean))
    return Array.from(models) as string[]
  }, [conversations])

  const handleRename = useCallback((id: string, newTitle: string) => {
    if (newTitle.trim() && onRename) {
      onRename(id, newTitle.trim())
    }
    setEditingId(null)
    setEditTitle('')
  }, [onRename])

  const handleDelete = useCallback((id: string) => {
    onDelete?.(id)
  }, [onDelete])

  const formatDate = (timestamp: string | Date | undefined) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  const getPreview = (content: string) => {
    const cleaned = content.replace(/[#*_`]/g, '').trim()
    return cleaned.length > 80 ? cleaned.slice(0, 80) + '...' : cleaned
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-3">
        <h2 className="font-semibold text-sm">Chat History</h2>
        {onNewChat && (
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onNewChat}
          >
            <MessageSquare className="h-4 w-4" />
          </Button>
        )}
      </div>

      <Separator />

      <div className="space-y-2 p-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 text-sm"
          />
        </div>

        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8 flex-1 justify-between text-xs">
                <Filter className="h-3.5 w-3.5 mr-1" />
                Sort: {sortBy}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuItem onClick={() => setSortBy('newest')}>Newest</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSortBy('oldest')}>Oldest</DropdownMenuItem>
              <DropdownMenuItem onClick={() => setSortBy('title')}>Title</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {uniqueModels.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 flex-1 justify-between text-xs">
                  {filterModel === 'all' ? 'All models' : filterModel}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuItem onClick={() => setFilterModel('all')}>All models</DropdownMenuItem>
                {uniqueModels.map((model) => (
                  <DropdownMenuItem key={model} onClick={() => setFilterModel(model)}>
                    {model}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}

          <Button
            variant={showFavoritesOnly ? 'default' : 'outline'}
            size="sm"
            className="h-8 px-2"
            onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
            title="Show favorites only"
          >
            <Star className={cn('h-3.5 w-3.5', showFavoritesOnly && 'fill-current')} />
          </Button>
        </div>
      </div>

      <Separator />

      <ScrollArea className="flex-1 px-2">
        {sortedConversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="rounded-full bg-muted p-3">
              <MessageSquare className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="mt-3 text-sm font-medium text-muted-foreground">No conversations</p>
            <p className="text-xs text-muted-foreground">
              {searchQuery ? 'Try a different search' : 'Start a new chat to begin'}
            </p>
          </div>
        ) : (
          <div className="space-y-1 py-2">
            {sortedConversations.map((conv) => (
              <div
                key={conv.id}
                className={cn(
                  'group flex items-start gap-3 rounded-lg px-3 py-2.5 text-sm cursor-pointer transition-colors',
                  activeId === conv.id
                    ? 'bg-accent text-accent-foreground'
                    : 'hover:bg-accent/50'
                )}
                onClick={() => onSelect?.(conv.id)}
              >
                <MessageSquare className="mt-0.5 size-4 shrink-0 text-muted-foreground" />

                <div className="flex-1 min-w-0">
                  {editingId === conv.id ? (
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => handleRename(conv.id, editTitle)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleRename(conv.id, editTitle)
                        }
                        if (e.key === 'Escape') {
                          setEditingId(null)
                          setEditTitle('')
                        }
                      }}
                      className="w-full bg-transparent text-sm outline-none"
                      autoFocus
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <>
                      <p className="font-medium truncate">{getPreview(conv.content)}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(conv.timestamp)}
                        </span>
                        {conv.model && (
                          <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                            {conv.model}
                          </Badge>
                        )}
                        {conv.feedback === 'up' && (
                          <Star className="h-3 w-3 fill-yellow-500 text-yellow-500" />
                        )}
                      </div>
                    </>
                  )}
                </div>

                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-6"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <MoreHorizontal className="size-3" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingId(conv.id)
                          setEditTitle(getPreview(conv.content))
                        }}
                      >
                        Rename
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(conv.id)
                        }}
                        className="text-destructive"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
