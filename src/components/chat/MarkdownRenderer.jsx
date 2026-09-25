import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import CodeBlock from './CodeBlock'
import KaTeXBlock from './KaTeXBlock'
import MermaidBlock from './MermaidBlock'
import ArtifactViewer from './ArtifactViewer'
import MediaEmbed from './MediaEmbed'
import Icon from '../../design/Iconography'

export default function MarkdownRenderer({ content, onFileUpload }) {
  const [renderedBlocks, setRenderedBlocks] = useState([])
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    parseContent(content)
  }, [content])

  const parseContent = useCallback((text) => {
    if (!text) return
    const lines = text.split('\n')
    const blocks = []
    let i = 0

    while (i < lines.length) {
      const line = lines[i]

      if (line.startsWith('```')) {
        const language = line.slice(3).trim()
        const codeLines = []
        i++
        while (i < lines.length && !lines[i].startsWith('```')) {
          codeLines.push(lines[i])
          i++
        }
        i++
        blocks.push({ type: 'code', language, content: codeLines.join('\n') })
      } else if (line.startsWith('$$') || line.startsWith('$')) {
        const mathLines = []
        i++
        while (i < lines.length && !lines[i].startsWith('$$') && !lines[i].startsWith('$')) {
          mathLines.push(lines[i])
          i++
        }
        i++
        blocks.push({ type: 'math', content: mathLines.join('\n'), display: line.startsWith('$$') })
      } else if (line.startsWith('```mermaid')) {
        const mermaidLines = []
        i++
        while (i < lines.length && !lines[i].startsWith('```')) {
          mermaidLines.push(lines[i])
          i++
        }
        i++
        blocks.push({ type: 'mermaid', content: mermaidLines.join('\n') })
      } else if (line.startsWith('```artifact') || line.startsWith('<artifact>')) {
        const artifactLines = []
        i++
        while (i < lines.length && !lines[i].startsWith('```') && !lines[i].startsWith('</artifact>')) {
          artifactLines.push(lines[i])
          i++
        }
        i++
        try {
          const artifact = JSON.parse(artifactLines.join('\n'))
          blocks.push({ type: 'artifact', content: artifact })
        } catch {
          blocks.push({ type: 'text', content: line })
        }
      } else if (line.startsWith('![')) {
        const match = line.match(/!\[(.*?)\]\((.*?)\)/)
        if (match) {
          blocks.push({ type: 'image', alt: match[1], src: match[2] })
        }
        i++
      } else if (line.startsWith('http')) {
        const urlMatch = line.match(/https?:\/\/[^\s]+/)
        if (urlMatch && /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(urlMatch[0])) {
          blocks.push({ type: 'image', src: urlMatch[0], alt: '' })
        } else if (urlMatch && /\.(mp3|wav|ogg|m4a)$/i.test(urlMatch[0])) {
          blocks.push({ type: 'audio', src: urlMatch[0] })
        } else if (urlMatch && /\.(mp4|webm|mov|avi)$/i.test(urlMatch[0])) {
          blocks.push({ type: 'video', src: urlMatch[0] })
        }
        i++
      } else if (line.trim()) {
        const textLines = []
        while (i < lines.length && lines[i].trim() && !lines[i].startsWith('```') && !lines[i].startsWith('$$') && !lines[i].startsWith('$') && !lines[i].startsWith('```mermaid') && !lines[i].startsWith('```artifact') && !lines[i].startsWith('<artifact>') && !lines[i].startsWith('![') && !lines[i].startsWith('http')) {
          textLines.push(lines[i])
          i++
        }
        if (textLines.length > 0) {
          blocks.push({ type: 'text', content: textLines.join('\n') })
        }
      } else {
        i++
      }
    }

    setRenderedBlocks(blocks)
  }, [])

  const copyAll = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [content])

  if (!content) return null

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={copyAll}
        style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          background: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-sm)',
          padding: '4px 8px',
          color: 'var(--astrovox-text-muted)',
          cursor: 'pointer',
          fontSize: '10px',
          fontFamily: 'inherit',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          zIndex: 10
        }}
        aria-label="Copy all content"
      >
        <Icon name="copy" size={12} />
        {copied ? 'Copied' : 'Copy'}
      </button>
      <div style={{ fontSize: '13px', lineHeight: '1.7', color: 'var(--astrovox-text)' }}>
        <AnimatePresence>
          {renderedBlocks.map((block, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.2, delay: index * 0.05 }}
              style={{ marginBottom: '12px' }}
            >
              {block.type === 'code' && (
                <CodeBlock language={block.language} value={block.content} />
              )}
              {block.type === 'math' && (
                <KaTeXBlock content={block.content} display={block.display} />
              )}
              {block.type === 'mermaid' && (
                <MermaidBlock content={block.content} />
              )}
              {block.type === 'artifact' && (
                <ArtifactViewer artifact={block.content} />
              )}
              {block.type === 'image' && (
                <MediaEmbed type="image" src={block.src} alt={block.alt} />
              )}
              {block.type === 'audio' && (
                <MediaEmbed type="audio" src={block.src} />
              )}
              {block.type === 'video' && (
                <MediaEmbed type="video" src={block.src} />
              )}
              {block.type === 'text' && (
                <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{block.content}</p>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
