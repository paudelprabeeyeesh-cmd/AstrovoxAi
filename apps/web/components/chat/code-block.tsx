'use client'
import { useEffect, useState } from 'react'
import { Check, Copy } from 'lucide-react'

interface CodeBlockProps {
  language: string
  code: string
}

export function CodeBlock({ language, code }: CodeBlockProps) {
  const [html, setHtml] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function highlight() {
      try {
        const mod = await import('shiki')
        const result = await (mod as any).codeToHtml?.(code, { lang: language, theme: 'github-dark' })
        if (!cancelled) setHtml(result || '')
      } catch {
        if (!cancelled) setHtml('')
      }
    }
    highlight()
    return () => { cancelled = true }
  }, [code, language])

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative my-4 rounded-lg border bg-muted/50 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-muted/80 border-b">
        <span className="text-xs text-muted-foreground font-mono">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div
        className="p-4 overflow-x-auto [&_pre]:!bg-transparent [&_pre]:!p-0 [&_code]:!text-sm"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  )
}
