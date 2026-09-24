'use client'
import { useState, useCallback } from 'react'
import { useChatStore } from '@/lib/store/chat-store'
import { useUIStore } from '@/lib/store/ui-store'
import {
  Search,
  Plus,
  MessageSquare,
  ChevronDown,
  ChevronRight,
  Trash2,
  MoreHorizontal,
  Pencil,
  GripVertical,
  Pin,
  PinOff,
  FolderOpen,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react'
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

interface Conversation {
  id: string
  title: string
  active: boolean
  pinned?: boolean
  folder?: string
}

const initialConversations: Conversation[] = [
  { id: '1', title: 'React Hooks Discussion', active: true, pinned: true },
  { id: '2', title: 'TypeScript Best Practices', active: false },
  { id: '3', title: 'Next.js App Router', active: false },
  { id: '4', title: 'Tailwind CSS Tips', active: false, pinned: true },
  { id: '5', title: 'API Integration Help', active: false },
  { id: '6', title: 'Database Schema Design', active: false },
  { id: '7', title: 'Authentication Flow', active: false },
  { id: '8', title: 'Performance Optimization', active: false },
]

const folders = [
  { id: 'work', name: 'Work', icon: FolderOpen },
  { id: 'personal', name: 'Personal', icon: FolderOpen },
  { id: 'projects', name: 'Projects', icon: FolderOpen },
]

export function Sidebar({
  open,
  setOpen,
  collapsed,
  setCollapsed,
}: {
  open: boolean
  setOpen: (open: boolean) => void
  collapsed: boolean
  setCollapsed: (collapsed: boolean) => void
}) {
  const [conversations, setConversations] = useState<Conversation[]>(initialConversations)
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['work', 'personal', 'projects']))

  const { setActiveConversation, deleteConversation, pinConversation, unpinConversation, moveConversationToFolder } =
    useChatStore()
  const { setSidebarOpen } = useUIStore()

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleRename = (id: string, newTitle: string) => {
    if (newTitle.trim()) {
      setConversations((prev) =>
        prev.map((conv) => (conv.id === id ? { ...conv, title: newTitle.trim() } : conv))
      )
    }
    setEditingId(null)
    setEditTitle('')
  }

  const handleDelete = (id: string) => {
    setConversations((prev) => prev.filter((conv) => conv.id !== id))
    deleteConversation(id)
  }

  const handlePin = (id: string, pinned: boolean) => {
    if (pinned) {
      pinConversation(id)
    } else {
      unpinConversation(id)
    }
    setConversations((prev) =>
      prev.map((conv) => (conv.id === id ? { ...conv, pinned: !pinned } : conv))
    )
  }

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, id: string) => {
    e.dataTransfer.setData('text/plain', id)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>, folderId: string | null) => {
    e.preventDefault()
    const id = e.dataTransfer.getData('text/plain')
    if (folderId) {
      moveConversationToFolder(id, folderId)
      setConversations((prev) =>
        prev.map((conv) => (conv.id === id ? { ...conv, folder: folderId } : conv))
      )
    }
  }

  const toggleFolder = (folderId: string) => {
    setExpandedFolders((prev) => {
      const next = new Set(prev)
      if (next.has(folderId)) {
        next.delete(folderId)
      } else {
        next.add(folderId)
      }
      return next
    })
  }

  const groupedConversations = conversations.reduce(
    (acc, conv) => {
      const folder = conv.folder || 'unfiled'
      if (!acc[folder]) {
        acc[folder] = []
      }
      acc[folder].push(conv)
      return acc
    },
    {} as Record<string, Conversation[]>
  )

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col',
          'border-r border-border bg-muted/40',
          'transition-all duration-300',
          'lg:relative lg:z-0',
          collapsed ? 'w-16' : 'w-64',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        <div className="flex h-14 items-center justify-between px-3">
          {!collapsed && (
            <span className="font-semibold text-sm">Conversations</span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto size-8"
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </Button>
        </div>

        <Separator />

        <div className="p-2">
          <Button
            variant="default"
            size="sm"
            className="w-full justify-start gap-2"
            onClick={() => {
              const newId = crypto.randomUUID()
              const newConv: Conversation = {
                id: newId,
                title: 'New Chat',
                active: true,
              }
              setConversations((prev) => [newConv, ...prev])
              setActiveConversation(newId)
              setSidebarOpen(false)
            }}
          >
            <Plus className="size-4" />
            {!collapsed && <span>New Chat</span>}
          </Button>
        </div>

        {!collapsed && (
          <div className="px-2 pb-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 size-4 text-muted-foreground" />
              <Input
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-2 text-sm"
              />
            </div>
          </div>
        )}

        <Separator />

        <ScrollArea className="flex-1 px-2 py-1">
          {!collapsed ? (
            <div className="space-y-1">
              {Object.entries(groupedConversations).map(([folder, convs]) => (
                <div key={folder}>
                  {folder !== 'unfiled' && (
                    <button
                      onClick={() => toggleFolder(folder)}
                      className="flex w-full items-center gap-1 px-2 py-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                    >
                      {expandedFolders.has(folder) ? (
                        <ChevronDown className="h-3 w-3" />
                      ) : (
                        <ChevronRight className="h-3 w-3" />
                      )}
                      <FolderOpen className="h-3 w-3" />
                      <span className="flex-1 capitalize">{folder}</span>
                      <span className="text-[10px]">{convs.length}</span>
                    </button>
                  )}

                  {(folder === 'unfiled' || expandedFolders.has(folder)) && (
                    <div className="space-y-1">
                      {convs
                        .filter((conv) =>
                          conv.title.toLowerCase().includes(searchQuery.toLowerCase())
                        )
                        .map((conv) => (
                          <div
                            key={conv.id}
                            draggable
                            onDragStart={(e) => handleDragStart(e, conv.id)}
                            onDragOver={handleDragOver}
                            onDrop={(e) => handleDrop(e, folder === 'unfiled' ? null : folder)}
                            className={cn(
                              'group flex items-center gap-2 rounded-md px-2 py-2 text-sm cursor-pointer transition-colors',
                              conv.active
                                ? 'bg-accent text-accent-foreground'
                                : 'hover:bg-accent/50'
                            )}
                            onClick={() => {
                              setActiveConversation(conv.id)
                              setConversations((prev) =>
                                prev.map((c) => ({
                                  ...c,
                                  active: c.id === conv.id,
                                }))
                              )
                            }}
                          >
                            <GripVertical className="size-3 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
                            <MessageSquare className="size-4 shrink-0" />

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
                                className="flex-1 bg-transparent text-sm outline-none"
                                autoFocus
                                onClick={(e) => e.stopPropagation()}
                              />
                            ) : (
                              <span className="flex-1 truncate">{conv.title}</span>
                            )}

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
                                      setEditTitle(conv.title)
                                    }}
                                  >
                                    <Pencil className="mr-2 h-4 w-4" />
                                    Rename
                                  </DropdownMenuItem>
                                  <DropdownMenuItem
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      handlePin(conv.id, conv.pinned || false)
                                    }}
                                  >
                                    {conv.pinned ? (
                                      <>
                                        <PinOff className="mr-2 h-4 w-4" />
                                        Unpin
                                      </>
                                    ) : (
                                      <>
                                        <Pin className="mr-2 h-4 w-4" />
                                        Pin
                                      </>
                                    )}
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
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-1">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => {
                    setActiveConversation(conv.id)
                    setConversations((prev) =>
                      prev.map((c) => ({ ...c, active: c.id === conv.id }))
                    )
                    setSidebarOpen(false)
                  }}
                  className={cn(
                    'flex w-full items-center justify-center rounded-md py-2 text-sm transition-colors',
                    conv.active
                      ? 'bg-accent text-accent-foreground'
                      : 'hover:bg-accent/50'
                  )}
                  title={conv.title}
                >
                  <MessageSquare className="size-4" />
                </button>
              ))}
            </div>
          )}
        </ScrollArea>

        <Separator />
        <div className="p-2">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2"
          >
            <MoreHorizontal className="size-4" />
            {!collapsed && <span>Settings</span>}
          </Button>
        </div>
      </aside>
    </>
  )
}
