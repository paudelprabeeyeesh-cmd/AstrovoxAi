'use client'
import ReactMarkdown from 'react-markdown'
import { CodeBlock } from './code-block'

interface MarkdownRendererProps {
  content: string
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-body text-sm leading-relaxed">
      <ReactMarkdown
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            if (match) {
              return <CodeBlock language={match[1]} code={String(children)} />
            }
            return <code className={className} {...props}>{children}</code>
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
