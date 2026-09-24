'use client'
import React, { useState, useMemo, useCallback, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeRaw from 'rehype-raw'
import rehypeHighlight from 'rehype-highlight'
import rehypeKatex from 'rehype-katex'
import { CodeBlock } from './code-block'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Maximize2, ChevronDown, ChevronRight, BookOpen, Clock, Braces } from 'lucide-react'
import { Button } from '@/components/ui/button'
import mermaid from 'mermaid'
import 'katex/dist/katex.min.css'
import 'highlight.js/styles/github-dark.css'

interface MarkdownRendererProps {
  content: string
  showWordCount?: boolean
  showTableOfContents?: boolean
  syntaxTheme?: string
}

type HeadingSlug = { id: string; text: string; level: number }

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function extractHeadings(content: string): HeadingSlug[] {
  const headings: HeadingSlug[] = []
  const regex = /^(#{1,3})\s+(.+)$/gm
  let match
  while ((match = regex.exec(content)) !== null) {
    const level = match[1].length
    const text = match[2].replace(/[#*`]/g, '').trim()
    const id = slugify(text)
    if (id && !headings.some((h) => h.id === id)) {
      headings.push({ id, text, level })
    }
  }
  return headings
}

function countWords(content: string): number {
  const plain = content
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]+`/g, ' ')
    .replace(/\$\$[\s\S]*?\$\$/g, ' ')
    .replace(/\$[^$\n]+\$/g, ' ')
    .replace(/[#*_~`\[\]()!>|-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return plain ? plain.split(' ').length : 0
}

const SYNTAX_THEMES = [
  { id: 'github-dark', name: 'GitHub Dark' },
  { id: 'github-light', name: 'GitHub Light' },
  { id: 'dracula', name: 'Dracula' },
  { id: 'monokai', name: 'Monokai' },
  { id: 'nord', name: 'Nord' },
  { id: 'solarized-dark', name: 'Solarized Dark' },
]

export function MarkdownRenderer({ content, showWordCount = false, showTableOfContents = false, syntaxTheme = 'github-dark' }: MarkdownRendererProps) {
  const [lightboxImage, setLightboxImage] = useState<string | null>(null)
  const [showToc, setShowToc] = useState(false)
  const [showThemePicker, setShowThemePicker] = useState(false)
  const [mermaidErrors, setMermaidErrors] = useState<Record<string, string>>({})

  const headings = useMemo(() => extractHeadings(content), [content])
  const wordCount = useMemo(() => countWords(content), [content])
  const readingTime = Math.max(1, Math.ceil(wordCount / 200))

  const scrollToHeading = useCallback((id: string) => {
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      el.classList.add('ring-2', 'ring-primary/30', 'rounded')
      setTimeout(() => el.classList.remove('ring-2', 'ring-primary/30', 'rounded'), 2000)
    }
  }, [])

  const renderMermaid = useCallback(async (code: string, id: string) => {
    try {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
      })
      const { svg } = await mermaid.render(`mermaid-${id}`, code)
      return svg
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      setMermaidErrors((prev) => ({ ...prev, [id]: errorMessage }))
      return null
    }
  }, [])

  return (
    <div className="markdown-body text-sm leading-relaxed">
      <div className="mb-3 flex items-center gap-3 flex-wrap">
        {showTableOfContents && headings.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowToc(!showToc)}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <BookOpen className="h-3 w-3" />
            Contents
            {showToc ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </Button>
        )}
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowThemePicker(!showThemePicker)}
            className="h-7 gap-1.5 px-2 text-xs text-muted-foreground hover:text-foreground"
          >
            <Braces className="h-3 w-3" />
            {syntaxTheme}
          </Button>
          {showThemePicker && (
            <div className="absolute top-full mt-1 z-50 rounded-md border border-border bg-background shadow-lg">
              {SYNTAX_THEMES.map((theme) => (
                <button
                  key={theme.id}
                  onClick={() => {
                    // theme change handled by parent or internal state
                    setShowThemePicker(false)
                  }}
                  className={`block w-full px-3 py-1.5 text-left text-xs hover:bg-muted ${
                    theme.id === syntaxTheme ? 'text-primary font-medium' : ''
                  }`}
                >
                  {theme.name}
                </button>
              ))}
            </div>
          )}
        </div>
        {showWordCount && (
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            {wordCount} words · {readingTime} min read
          </span>
        )}
      </div>

      {showToc && headings.length > 0 && (
        <div className="mb-4 rounded-lg border border-border bg-muted/30 p-3">
          <div className="text-xs font-semibold text-muted-foreground mb-2">On this page</div>
          <div className="space-y-1">
            {headings.map((h) => (
              <button
                key={h.id}
                onClick={() => scrollToHeading(h.id)}
                className={`block text-left text-xs transition-colors hover:text-foreground ${
                  h.level === 1 ? 'font-medium text-foreground' : h.level === 2 ? 'pl-3 text-muted-foreground' : 'pl-6 text-muted-foreground/70'
                }`}
              >
                {h.text}
              </button>
            ))}
          </div>
        </div>
      )}

      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeHighlight, rehypeKatex]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const codeString = String(children).replace(/\n$/, '')

            if (match && match[1] === 'mermaid') {
              return <MermaidDiagram code={codeString} />
            }

            if (match) {
              return <CodeBlock language={match[1]} code={codeString} />
            }

            return (
              <code
                className="rounded-md bg-muted/80 px-1.5 py-0.5 font-mono text-xs text-foreground"
                {...props}
              >
                {children}
              </code>
            )
          },
          h1({ children }) {
            const text = String(children).replace(/[#*`]/g, '').trim()
            const id = slugify(text)
            return (
              <h1 id={id} className="scroll-mt-20 text-2xl font-bold mt-6 mb-4 pb-2 border-b border-border">
                {children}
              </h1>
            )
          },
          h2({ children }) {
            const text = String(children).replace(/[#*`]/g, '').trim()
            const id = slugify(text)
            return (
              <h2 id={id} className="scroll-mt-20 text-xl font-semibold mt-5 mb-3">
                {children}
              </h2>
            )
          },
          h3({ children }) {
            const text = String(children).replace(/[#*`]/g, '').trim()
            const id = slugify(text)
            return (
              <h3 id={id} className="scroll-mt-20 text-lg font-medium mt-4 mb-2">
                {children}
              </h3>
            )
          },
          table({ children }) {
            return (
              <div className="my-4 overflow-x-auto rounded-lg border border-border">
                <table className="min-w-full divide-y divide-border">{children}</table>
              </div>
            )
          },
          thead({ children }) {
            return <thead className="bg-muted/50">{children}</thead>
          },
          tbody({ children }) {
            return <tbody className="divide-y divide-border">{children}</tbody>
          },
          tr({ children }) {
            return <tr className="hover:bg-muted/30 transition-colors">{children}</tr>
          },
          th({ children }) {
            return (
              <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {children}
              </th>
            )
          },
          td({ children }) {
            return <td className="px-4 py-2 text-sm">{children}</td>
          },
          input({ type, checked, disabled, ...props }) {
            if (type === 'checkbox') {
              return (
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={disabled}
                  className="mr-2 h-4 w-4 rounded border-border text-primary focus:ring-primary"
                  readOnly
                />
              )
            }
            return <input type={type} {...props} />
          },
          ul({ children, ...props }) {
            const hasCheckbox = Array.from(children as React.ReactNodeArray).some((child) =>
              typeof child === 'object' && child !== null && 'props' in child && child.props?.type === 'checkbox'
            )
            if (hasCheckbox) {
              return <ul className="my-2 space-y-1">{children}</ul>
            }
            return <ul className="my-2 list-disc space-y-1 pl-6" {...props}>{children}</ul>
          },
          ol({ children, ...props }) {
            return <ol className="my-2 list-decimal space-y-1 pl-6" {...props}>{children}</ol>
          },
          li({ children }) {
            return <li className="leading-relaxed">{children}</li>
          },
          a({ href, children }) {
            const isExternal = href?.startsWith('http')
            return (
              <a
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                className="text-primary underline underline-offset-2 hover:text-primary/80 transition-colors"
              >
                {children}
              </a>
            )
          },
          img({ src, alt }) {
            return (
              <div className="relative my-4 inline-block">
                <img
                  src={src}
                  alt={alt || 'Image'}
                  className="max-w-full rounded-lg cursor-pointer hover:opacity-90 transition-opacity"
                  onClick={() => setLightboxImage(src || '')}
                />
                <Button
                  variant="secondary"
                  size="sm"
                  className="absolute top-2 right-2 h-8 w-8 p-0 bg-black/50 hover:bg-black/70 text-white"
                  onClick={() => setLightboxImage(src || '')}
                >
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </div>
            )
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-4 border-l-4 border-primary/30 pl-4 italic text-muted-foreground">
                {children}
              </blockquote>
            )
          },
          hr() {
            return <hr className="my-6 border-border" />
          },
          pre({ children }) {
            return <pre className="!bg-muted/50 !p-0 !rounded-lg overflow-x-auto">{children}</pre>
          },
          p({ children }) {
            return <p className="mb-3 last:mb-0">{children}</p>
          },
        }}
      >
        {content}
      </ReactMarkdown>

      <Dialog open={!!lightboxImage} onOpenChange={(open) => !open && setLightboxImage(null)}>
        <DialogContent className="max-w-5xl p-0 bg-transparent border-none shadow-none">
          {lightboxImage && (
            <img
              src={lightboxImage}
              alt="Lightbox"
              className="max-w-full max-h-[90vh] rounded-lg object-contain"
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function MermaidDiagram({ code }: { code: string }) {
  const [svg, setSvg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function render() {
      try {
        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          securityLevel: 'loose',
        })
        const { svg: rendered } = await mermaid.render(`mermaid-${Date.now()}`, code)
        if (!cancelled) setSvg(rendered)
      } catch (err) {
        if (!cancelled) {
          const errorMessage = err instanceof Error ? err.message : String(err)
          setError(errorMessage)
        }
      }
    }
    render()
    return () => { cancelled = true }
  }, [code])

  if (error) {
    return (
      <div className="my-4 rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950/30 p-4">
        <p className="text-sm text-red-600 dark:text-red-400">Mermaid diagram error: {error}</p>
      </div>
    )
  }

  if (!svg) {
    return (
      <div className="my-4 flex items-center justify-center rounded-lg border border-border bg-muted/30 p-8">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div
      className="my-4 flex justify-center overflow-x-auto rounded-lg border border-border bg-muted/30 p-4"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}
