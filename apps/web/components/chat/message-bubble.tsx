'use client'
import { useState, useCallback } from 'react'
import { Message } from './types'
import { User, Bot, Copy, RefreshCw, Edit3, ThumbsUp, ThumbsDown, MoreHorizontal, Check, Square } from 'lucide-react'
import { MarkdownRenderer } from './markdown-renderer'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'

interface MessageBubbleProps {
  message: Message
  onRegenerate?: (messageId: string) => void
  onEdit?: (messageId: string, content: string) => void
  onCopy?: (content: string) => void
  onFeedback?: (messageId: string, feedback: 'up' | 'down' | null) => void
  onStop?: () => void
  isStreaming?: boolean
}

const avatarColors: Record<string, string> = {
  user: 'bg-blue-500 text-white',
  assistant: 'bg-gradient-to-br from-purple-500 to-pink-500 text-white',
  system: 'bg-amber-500 text-white',
}

const avatarIcons: Record<string, React.ReactNode> = {
  user: <User className="h-4 w-4" />,
  assistant: <Bot className="h-4 w-4" />,
  system: '⚙️',
}

export function MessageBubble({
  message,
  onRegenerate,
  onEdit,
  onCopy,
  onFeedback,
  onStop,
  isStreaming,
}: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const [showActions, setShowActions] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    if (onCopy) {
      onCopy(message.content)
    } else {
      await navigator.clipboard.writeText(message.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }, [message.content, onCopy])

  const handleFeedback = useCallback(
    (feedback: 'up' | 'down' | null) => {
      onFeedback?.(message.id, feedback)
    },
    [message.id, onFeedback]
  )

  const formatTime = (timestamp?: string | Date) => {
    if (!timestamp) return ''
    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div
      className={`group flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <Avatar className={`h-8 w-8 shrink-0 ${avatarColors[message.role] || avatarColors.assistant}`}>
        <AvatarFallback className={avatarColors[message.role] || avatarColors.assistant}>
          {avatarIcons[message.role] || avatarIcons.assistant}
        </AvatarFallback>
      </Avatar>

      <div className={`flex max-w-[80%] flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {!isUser && (
          <div className="mb-1 flex items-center gap-2">
            <span className="text-xs font-medium text-foreground">
              {message.role === 'assistant' ? 'Assistant' : 'System'}
            </span>
            {message.model && (
              <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                {message.model}
              </span>
            )}
            {message.timestamp && (
              <span className="text-[10px] text-muted-foreground">{formatTime(message.timestamp)}</span>
            )}
          </div>
        )}

        <div
          className={`relative rounded-2xl px-4 py-2.5 ${
            isSystem
              ? 'bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-100'
              : isUser
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground'
          }`}
        >
          {isSystem && (
            <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
              <span>⚙️</span>
              <span>System</span>
            </div>
          )}

          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}

          {isStreaming && isUser === false && (
            <span className="ml-1 inline-block h-4 w-2 animate-pulse bg-primary" />
          )}
        </div>

        <div className="mt-1 flex items-center gap-2">
          {message.timestamp && isUser && (
            <span className="text-xs text-muted-foreground">{formatTime(message.timestamp)}</span>
          )}

          <div
            className={`flex items-center gap-1 transition-opacity ${
              showActions || isStreaming ? 'opacity-100' : 'opacity-0'
            }`}
          >
            {isStreaming && onStop && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onStop}
                className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
              >
                <Square className="h-3 w-3" />
                Stop
              </Button>
            )}

            {!isStreaming && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                  title="Copy"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
                </Button>

                {isUser && onEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onEdit(message.id, message.content)}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                    title="Edit"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                  </Button>
                )}

                {!isUser && onRegenerate && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRegenerate(message.id)}
                    className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                    title="Regenerate"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                  </Button>
                )}

                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                      title="More actions"
                    >
                      <MoreHorizontal className="h-3.5 w-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem onClick={handleCopy}>
                      <Copy className="mr-2 h-4 w-4" />
                      Copy text
                    </DropdownMenuItem>
                    {!isUser && onRegenerate && (
                      <DropdownMenuItem onClick={() => onRegenerate(message.id)}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Regenerate
                      </DropdownMenuItem>
                    )}
                    {isUser && onEdit && (
                      <DropdownMenuItem onClick={() => onEdit(message.id, message.content)}>
                        <Edit3 className="mr-2 h-4 w-4" />
                        Edit message
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => handleFeedback('up')}>
                      <ThumbsUp className="mr-2 h-4 w-4" />
                      Good response
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleFeedback('down')}>
                      <ThumbsDown className="mr-2 h-4 w-4" />
                      Bad response
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                {!isUser && (
                  <div className="flex items-center gap-0.5">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFeedback('up')}
                      className={`h-7 w-7 p-0 ${
                        message.feedback === 'up' ? 'text-green-500' : 'text-muted-foreground hover:text-foreground'
                      }`}
                      title="Thumbs up"
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFeedback('down')}
                      className={`h-7 w-7 p-0 ${
                        message.feedback === 'down' ? 'text-red-500' : 'text-muted-foreground hover:text-foreground'
                      }`}
                      title="Thumbs down"
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
