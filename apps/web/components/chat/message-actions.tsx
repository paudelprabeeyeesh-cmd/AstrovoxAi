'use client'
import { useState, useEffect, useCallback } from 'react'
import { Message } from './types'
import {
  Copy,
  RefreshCw,
  Edit3,
  ThumbsUp,
  ThumbsDown,
  Check,
  Square,
  Keyboard,
  Command,
  Share2,
  Trash2,
  Bookmark,
  MoreHorizontal,
  Star,
  Smile,
  Laugh,
  Heart,
  Frown,
  Undo2,
  MessageSquare,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface MessageActionsProps {
  message: Message
  onRegenerate?: (messageId: string) => void
  onEdit?: (messageId: string, content: string) => void
  onCopy?: (content: string) => void
  onFeedback?: (messageId: string, feedback: 'up' | 'down' | null) => void
  onStop?: () => void
  onDelete?: (messageId: string) => void
  onBookmark?: (messageId: string) => void
  onShare?: (messageId: string) => void
  isStreaming?: boolean
  isBookmarked?: boolean
}

const REACTIONS = [
  { emoji: '👍', label: 'Approve', icon: Smile },
  { emoji: '😂', label: 'Nice', icon: Laugh },
  { emoji: '❤️', label: 'Love', icon: Heart },
  { emoji: '👎', label: 'Disapprove', icon: Frown },
]

const SHORTCUTS = [
  { key: 'C', label: 'Copy', icon: Copy, action: 'copy', mod: true },
  { key: 'R', label: 'Regenerate', icon: RefreshCw, action: 'regenerate', mod: true },
  { key: 'E', label: 'Edit', icon: Edit3, action: 'edit', mod: true },
  { key: 'B', label: 'Bookmark', icon: Bookmark, action: 'bookmark', mod: true },
  { key: 'S', label: 'Share', icon: Share2, action: 'share', mod: true },
  { key: '↑', label: 'Rate up', icon: ThumbsUp, action: 'feedback-up' },
  { key: '↓', label: 'Rate down', icon: ThumbsDown, action: 'feedback-down' },
  { key: 'Del', label: 'Delete', icon: Trash2, action: 'delete', mod: true },
]

export function MessageActions({
  message,
  onRegenerate,
  onEdit,
  onCopy,
  onFeedback,
  onStop,
  onDelete,
  onBookmark,
  onShare,
  isStreaming,
  isBookmarked,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)
  const [bookmarked, setBookmarked] = useState(isBookmarked || false)
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)
  const [reaction, setReaction] = useState<string | null>(null)
  const [showReactions, setShowReactions] = useState(false)
  const [showUndo, setShowUndo] = useState(false)
  const [lastAction, setLastAction] = useState<string | null>(null)

  const handleCopy = useCallback(async () => {
    if (onCopy) {
      onCopy(message.content)
    } else {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setLastAction('copy')
      setShowUndo(true)
      setTimeout(() => {
        setCopied(false)
        setShowUndo(false)
      }, 2000)
    }
  }, [message.content, onCopy])

  const handleBookmark = useCallback(() => {
    setBookmarked((prev) => !prev)
    onBookmark?.(message.id)
    setLastAction(bookmarked ? 'remove bookmark' : 'bookmark')
  }, [message.id, onBookmark, bookmarked])

  const handleFeedback = useCallback(
    (type: 'up' | 'down') => {
      setFeedback((prev) => (prev === type ? null : type))
      onFeedback?.(message.id, type)
    },
    [message.id, onFeedback]
  )

  const handleReaction = useCallback((emoji: string) => {
    setReaction((prev) => (prev === emoji ? null : emoji))
  }, [])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!e.target || (e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') {
        return
      }

      const targetMessage = (e.target as HTMLElement).closest('[data-message-id]')
      if (!targetMessage || targetMessage.getAttribute('data-message-id') !== message.id) {
        return
      }

      const mod = e.metaKey || e.ctrlKey
      const key = e.key.toLowerCase()

      if (mod && key === 'c') {
        e.preventDefault()
        handleCopy()
      } else if (mod && key === 'r' && onRegenerate) {
        e.preventDefault()
        onRegenerate(message.id)
      } else if (mod && key === 'e' && onEdit) {
        e.preventDefault()
        onEdit(message.id, message.content)
      } else if (mod && key === 'b' && onBookmark) {
        e.preventDefault()
        handleBookmark()
      } else if (mod && key === 's' && onShare) {
        e.preventDefault()
        onShare?.(message.id)
      } else if (mod && key === 'delete' && onDelete) {
        e.preventDefault()
        onDelete?.(message.id)
      } else if (e.key === 'ArrowUp' && onFeedback && message.role === 'assistant') {
        e.preventDefault()
        handleFeedback('up')
      } else if (e.key === 'ArrowDown' && onFeedback && message.role === 'assistant') {
        e.preventDefault()
        handleFeedback('down')
      }
    },
    [message.id, message.content, message.role, handleCopy, onRegenerate, onEdit, onFeedback, onDelete, onBookmark, onShare, handleBookmark, handleFeedback]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const isUser = message.role === 'user'

  return (
    <TooltipProvider>
      <div
        className="flex items-center gap-0.5 transition-opacity"
        data-message-id={message.id}
      >
        {isStreaming && onStop && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={onStop}
                className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
              >
                <Square className="h-3 w-3" />
                Stop
              </Button>
            </TooltipTrigger>
            <TooltipContent>Stop generating</TooltipContent>
          </Tooltip>
        )}

        {showUndo && lastAction && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setCopied(false)
                  setShowUndo(false)
                }}
                className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
              >
                <Undo2 className="h-3 w-3" />
                Undo {lastAction}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Undo</TooltipContent>
          </Tooltip>
        )}

        {!isStreaming && (
          <>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                >
                  {copied ? (
                    <Check className="h-3.5 w-3.5 text-green-500" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent className="flex items-center gap-2">
                <span>Copy</span>
                <kbd className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">⌘C</kbd>
              </TooltipContent>
            </Tooltip>

            {isUser && onEdit && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(message.id, message.content)}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="flex items-center gap-2">
                  <span>Edit</span>
                  <kbd className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">⌘E</kbd>
                </TooltipContent>
              </Tooltip>
            )}

            {!isUser && onRegenerate && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRegenerate(message.id)}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="flex items-center gap-2">
                  <span>Regenerate</span>
                  <kbd className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">⌘R</kbd>
                </TooltipContent>
              </Tooltip>
            )}

            {message.role === 'assistant' && (
              <div className="flex items-center gap-0.5">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFeedback('up')}
                      className={cn(
                        'h-7 w-7 p-0',
                        feedback === 'up' || message.feedback === 'up'
                          ? 'text-green-500'
                          : 'text-muted-foreground hover:text-foreground'
                      )}
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="flex items-center gap-2">
                    <span>Good response</span>
                    <kbd className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">↑</kbd>
                  </TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFeedback('down')}
                      className={cn(
                        'h-7 w-7 p-0',
                        feedback === 'down' || message.feedback === 'down'
                          ? 'text-red-500'
                          : 'text-muted-foreground hover:text-foreground'
                      )}
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent className="flex items-center gap-2">
                    <span>Bad response</span>
                    <kbd className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">↓</kbd>
                  </TooltipContent>
                </Tooltip>
              </div>
            )}

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                >
                  <MoreHorizontal className="h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                {onBookmark && (
                  <DropdownMenuItem onClick={handleBookmark}>
                    <Bookmark className={cn('mr-2 h-4 w-4', bookmarked && 'fill-current')} />
                    {bookmarked ? 'Bookmarked' : 'Bookmark'}
                    <kbd className="ml-auto text-[10px] text-muted-foreground">⌘B</kbd>
                  </DropdownMenuItem>
                )}
                {onShare && (
                  <DropdownMenuItem onClick={() => onShare?.(message.id)}>
                    <Share2 className="mr-2 h-4 w-4" />
                    Share
                    <kbd className="ml-auto text-[10px] text-muted-foreground">⌘S</kbd>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                {onDelete && (
                  <DropdownMenuItem onClick={() => onDelete?.(message.id)} className="text-destructive">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                    <kbd className="ml-auto text-[10px] text-muted-foreground">⌘Del</kbd>
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowShortcuts(!showShortcuts)}
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                >
                  <Keyboard className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1 text-xs">
                  {SHORTCUTS.filter((s) => {
                    if (s.action === 'copy') return true
                    if (s.action === 'edit') return isUser && onEdit
                    if (s.action === 'regenerate') return !isUser && onRegenerate
                    if (s.action === 'bookmark') return !!onBookmark
                    if (s.action === 'share') return !!onShare
                    if (s.action === 'delete') return !!onDelete
                    if (s.action === 'feedback-up' || s.action === 'feedback-down') return message.role === 'assistant'
                    return false
                  }).map((shortcut) => (
                    <div key={shortcut.action} className="flex items-center justify-between gap-4">
                      <span className="flex items-center gap-1">
                        <shortcut.icon className="h-3 w-3" />
                        {shortcut.label}
                      </span>
                      <kbd className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
                        {shortcut.mod ? '⌘' : ''}{shortcut.key}
                      </kbd>
                    </div>
                  ))}
                </div>
              </TooltipContent>
            </Tooltip>
          </>
        )}
      </div>
    </TooltipProvider>
  )
}
