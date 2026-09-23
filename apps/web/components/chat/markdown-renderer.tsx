'use client'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize from 'rehype-sanitize'
import { CodeBlock } from './code-block'
import { useState } from 'react'
import { Dialog, DialogContent } from '@/components/ui/dialog'
import { Maximize2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface MarkdownRendererProps {
  content: string
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const [lightboxImage, setLightboxImage] = useState<string | null>(null)

  return (
    <div className="markdown-body text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeSanitize]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const codeString = String(children).replace(/\n$/, '')

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
