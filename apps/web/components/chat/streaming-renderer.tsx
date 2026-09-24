'use client'
import { useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { MarkdownRenderer } from './markdown-renderer'
import { Brain, Sparkles, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface StreamingRendererProps {
  content: string
  isStreaming?: boolean
  thinking?: boolean
  speed?: number
  onComplete?: () => void
  animationMode?: 'cursor' | 'word' | 'fade'
  showThinking?: boolean
  thinkingContent?: string
}

const cursorVariants = {
  initial: { opacity: 1, width: 6 },
  animate: {
    opacity: [1, 0],
    width: [6, 2],
    transition: {
      duration: 0.8,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
}

const wordVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.03,
      duration: 0.2,
      ease: 'easeOut',
    },
  }),
}

export function StreamingRenderer({
  content,
  isStreaming = false,
  thinking = false,
  onComplete,
  animationMode = 'cursor',
  showThinking = false,
  thinkingContent,
}: StreamingRendererProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const prevLengthRef = useRef(0)
  const [wordIndex, setWordIndex] = useState(0)
  const [showChainOfThought, setShowChainOfThought] = useState(false)

  const words = content.split(/(\s+)/)

  const smoothScrollToBottom = useCallback(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const isNearBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight < 100

    if (isNearBottom) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [])

  useEffect(() => {
    if (isStreaming && animationMode === 'word') {
      const interval = setInterval(() => {
        setWordIndex((prev) => {
          if (prev >= words.length) {
            clearInterval(interval)
            return prev
          }
          return prev + 1
        })
      }, 30)

      return () => clearInterval(interval)
    }
  }, [content, isStreaming, animationMode, words.length])

  useEffect(() => {
    if (isStreaming && content.length > prevLengthRef.current) {
      smoothScrollToBottom()
    }
    prevLengthRef.current = content.length

    if (!isStreaming && content.length > 0 && onComplete) {
      const timer = setTimeout(onComplete, 100)
      return () => clearTimeout(timer)
    }
  }, [content, isStreaming, smoothScrollToBottom, onComplete])

  useEffect(() => {
    if (showThinking && thinkingContent) {
      setShowChainOfThought(true)
    }
  }, [showThinking, thinkingContent])

  if (thinking && showChainOfThought && thinkingContent) {
    return (
      <div className="flex flex-col gap-3 rounded-2xl bg-muted/50 px-4 py-3">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-muted-foreground animate-pulse" />
          <span className="text-sm font-medium text-muted-foreground">Thinking</span>
          <Badge variant="outline" className="text-[10px]">
            Chain of Thought
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground italic pl-6 border-l-2 border-muted-foreground/30">
          {thinkingContent}
        </div>
      </div>
    )
  }

  if (thinking) {
    return (
      <div className="flex items-center gap-3 rounded-2xl bg-muted px-4 py-3">
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
        </div>
        <span className="text-sm text-muted-foreground">Thinking</span>
        {showThinking && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowChainOfThought(!showChainOfThought)}
            className="h-6 px-2 text-xs"
          >
            <Sparkles className="h-3 w-3 mr-1" />
            Show reasoning
          </Button>
        )}
      </div>
    )
  }

  const renderContent = () => {
    if (animationMode === 'word' && isStreaming) {
      const visibleWords = words.slice(0, wordIndex)
      return (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-wrap gap-1"
        >
          {visibleWords.map((word, i) => (
            <motion.span
              key={i}
              custom={i}
              variants={wordVariants}
              initial="hidden"
              animate="visible"
              className={cn(
                'inline-block',
                word.match(/^\s+$/) ? 'whitespace-pre' : ''
              )}
            >
              {word}
            </motion.span>
          ))}
        </motion.div>
      )
    }

    return <MarkdownRenderer content={content} />
  }

  return (
    <div ref={containerRef} className="flex max-h-[600px] flex-col gap-1 overflow-y-auto">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {renderContent()}
      </motion.div>

      <AnimatePresence>
        {isStreaming && animationMode === 'cursor' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="ml-1 flex items-center"
          >
            <motion.span
              variants={cursorVariants}
              initial="initial"
              animate="animate"
              className="inline-block h-4 bg-primary"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {isStreaming && animationMode === 'word' && (
        <div className="ml-1 flex items-center gap-2 text-xs text-muted-foreground">
          <Zap className="h-3 w-3 animate-pulse" />
          <span>Streaming...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
