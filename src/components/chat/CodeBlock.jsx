import { useState, useEffect, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { createHighlighter, codeToHtml } from 'shiki'
import Icon from '../../design/Iconography'

let shikiHighlighter = null

async function getHighlighter() {
  if (shikiHighlighter) return shikiHighlighter
  try {
    shikiHighlighter = await createHighlighter({
      themes: ['dark-plus', 'light-plus'],
      langs: ['javascript', 'typescript', 'python', 'rust', 'go', 'java', 'cpp', 'c', 'html', 'css', 'json', 'yaml', 'markdown', 'bash', 'sql', 'jsx', 'tsx', 'vue', 'svelte']
    })
    return shikiHighlighter
  } catch (err) {
    console.warn('Shiki initialization failed:', err)
    return null
  }
}

export default function CodeBlock({ language, value }) {
  const [copied, setCopied] = useState(false)
  const [highlighted, setHighlighted] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function highlight() {
      setIsLoading(true)
      const highlighter = await getHighlighter()
      if (cancelled || !highlighter) {
        setIsLoading(false)
        return
      }
      try {
        const lang = language && highlighter.getLoadedLanguages().includes(language)
          ? language
          : 'text'
        const html = highlighter.codeToHtml(value, {
          lang,
          theme: 'dark-plus'
        })
        if (!cancelled) {
          setHighlighted(html)
          setIsLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setHighlighted(null)
          setIsLoading(false)
        }
      }
    }
    highlight()
    return () => { cancelled = true }
  }, [language, value])

  const copyCode = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }, [value])

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        marginTop: '12px',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        overflow: 'hidden',
        backgroundColor: 'var(--astrovox-code)'
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          backgroundColor: 'var(--astrovox-surface)',
          borderBottom: '1px solid var(--astrovox-border)'
        }}
      >
        <span
          style={{
            fontSize: '11px',
            color: 'var(--astrovox-text-muted)',
            fontFamily: 'var(--astrovox-font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}
        >
          {language || 'code'}
        </span>
        <button
          onClick={copyCode}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: 'transparent',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)',
            padding: '4px 8px',
            color: 'var(--astrovox-text-muted)',
            cursor: 'pointer',
            fontSize: '10px',
            fontFamily: 'inherit'
          }}
          aria-label="Copy code"
        >
          <Icon name="copy" size={12} />
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      {isLoading ? (
        <pre
          style={{
            margin: 0,
            padding: '16px',
            overflowX: 'auto',
            fontSize: '12px',
            lineHeight: '1.6',
            color: 'var(--astrovox-code-text)',
            fontFamily: 'var(--astrovox-font-mono)'
          }}
        >
          <code>{value}</code>
        </pre>
      ) : highlighted ? (
        <div
          style={{
            margin: 0,
            padding: '16px',
            overflowX: 'auto',
            fontSize: '12px',
            lineHeight: '1.6'
          }}
          dangerouslySetInnerHTML={{ __html: highlighted }}
        />
      ) : (
        <pre
          style={{
            margin: 0,
            padding: '16px',
            overflowX: 'auto',
            fontSize: '12px',
            lineHeight: '1.6',
            color: 'var(--astrovox-code-text)',
            fontFamily: 'var(--astrovox-font-mono)'
          }}
        >
          <code>{value}</code>
        </pre>
      )}
    </motion.div>
  )
}
