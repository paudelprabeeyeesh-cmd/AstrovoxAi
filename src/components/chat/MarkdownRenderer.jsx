import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import rehypeHighlight from 'rehype-highlight'
import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkRehype from 'remark-rehype'
import rehypeStringify from 'rehype-stringify'
import rehypeRaw from 'rehype-raw'
import Icon from '../../design/Iconography'
import CodeBlock from './CodeBlock'
import KaTeXBlock from './KaTeXBlock'
import MermaidBlock from './MermaidBlock'
import ArtifactViewer from './ArtifactViewer'
import MediaEmbed from './MediaEmbed'
import { useMathAndDiagrams } from '../../utils/mathAndDiagrams'

const MERMAID_PATTERN = /```mermaid\n([\s\S]*?)```/g
const ARTIFACT_PATTERN = /```artifact\n([\s\S]*?)```/g
const MATH_PATTERN = /(\$\$[\s\S]*?\$\$|\$[^\$\n]*?\$)/g
const CODE_PATTERN = /```(\w+)?\n([\s\S]*?)```/g

export default function MarkdownRenderer({ content, onFileUpload }) {
  useMathAndDiagrams()
  const [renderedBlocks, setRenderedBlocks] = useState([])
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    parseContent(content || '')
  }, [content])

  const parseContent = useCallback((text) => {
    if (!text) {
      setRenderedBlocks([])
      return
    }

    const blocks = []
    let remaining = text

    while (remaining.length > 0) {
      let matched = false

      const mermaidMatch = remaining.match(/^```mermaid\n([\s\S]*?)```/)
      if (mermaidMatch) {
        blocks.push({ type: 'mermaid', content: mermaidMatch[1].trim() })
        remaining = remaining.slice(mermaidMatch[0].length).trimStart()
        matched = true
        continue
      }

      const artifactMatch = remaining.match(/^```artifact\n([\s\S]*?)```/)
      if (artifactMatch) {
        try {
          const artifact = JSON.parse(artifactMatch[1])
          blocks.push({ type: 'artifact', content: artifact })
        } catch {
          blocks.push({ type: 'text', content: artifactMatch[0] })
        }
        remaining = remaining.slice(artifactMatch[0].length).trimStart()
        matched = true
        continue
      }

      const codeMatch = remaining.match(/^```(\w+)?\n([\s\S]*?)```/)
      if (codeMatch) {
        blocks.push({ type: 'code', language: codeMatch[1] || '', content: codeMatch[2].trim() })
        remaining = remaining.slice(codeMatch[0].length).trimStart()
        matched = true
        continue
      }

      const mathBlockMatch = remaining.match(/^\$\$([\s\S]*?)\$\$/)
      if (mathBlockMatch) {
        blocks.push({ type: 'math', content: mathBlockMatch[1].trim(), display: true })
        remaining = remaining.slice(mathBlockMatch[0].length).trimStart()
        matched = true
        continue
      }

      const inlineMathMatch = remaining.match(/^\$([^\$\n]+?)\$/)
      if (inlineMathMatch) {
        blocks.push({ type: 'math', content: inlineMathMatch[1].trim(), display: false })
        remaining = remaining.slice(inlineMathMatch[0].length).trimStart()
        matched = true
        continue
      }

      const imageMatch = remaining.match(/^!\[(.*?)\]\((.*?)\)/)
      if (imageMatch) {
        blocks.push({ type: 'image', alt: imageMatch[1], src: imageMatch[2] })
        remaining = remaining.slice(imageMatch[0].length).trimStart()
        matched = true
        continue
      }

      const urlImageMatch = remaining.match(/^(https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|webp|svg))(\s|$)/i)
      if (urlImageMatch) {
        blocks.push({ type: 'image', src: urlImageMatch[1], alt: '' })
        remaining = remaining.slice(urlImageMatch[0].length).trimStart()
        matched = true
        continue
      }

      const urlAudioMatch = remaining.match(/^(https?:\/\/[^\s]+\.(mp3|wav|ogg|m4a))(\s|$)/i)
      if (urlAudioMatch) {
        blocks.push({ type: 'audio', src: urlAudioMatch[1] })
        remaining = remaining.slice(urlAudioMatch[0].length).trimStart()
        matched = true
        continue
      }

      const urlVideoMatch = remaining.match(/^(https?:\/\/[^\s]+\.(mp4|webm|mov|avi))(\s|$)/i)
      if (urlVideoMatch) {
        blocks.push({ type: 'video', src: urlVideoMatch[1] })
        remaining = remaining.slice(urlVideoMatch[0].length).trimStart()
        matched = true
        continue
      }

      const newlineIndex = remaining.indexOf('\n')
      const nextBlockStart = remaining.search(/^```|^\$\$|^\$|^!\[|^https?:\/\//)

      if (nextBlockStart === -1) {
        const text = remaining.trim()
        if (text) {
          blocks.push({ type: 'text', content: text })
        }
        break
      }

      if (nextBlockStart > 0) {
        const textSegment = remaining.slice(0, nextBlockStart === -1 ? remaining.length : nextBlockStart).trim()
        if (textSegment) {
          blocks.push({ type: 'text', content: textSegment })
        }
        remaining = remaining.slice(nextBlockStart).trimStart()
        matched = true
        continue
      }

      if (!matched) {
        const text = remaining.trim()
        if (text) {
          blocks.push({ type: 'text', content: text })
        }
        break
      }
    }

    setRenderedBlocks(blocks)
  }, [])

  const copyAll = useCallback(async () => {
    if (!content) return
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
              transition={{ duration: 0.2, delay: Math.min(index * 0.03, 0.3) }}
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
                <div style={{ whiteSpace: 'pre-wrap' }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[
                      [rehypeKatex, { strict: false }],
                      [rehypeHighlight, { detect: true }]
                    ]}
                    components={{
                      p: ({ children }) => <p style={{ margin: '0 0 8px 0' }}>{children}</p>,
                      ul: ({ children }) => <ul style={{ margin: '0 0 8px 0', paddingLeft: '20px' }}>{children}</ul>,
                      ol: ({ children }) => <ol style={{ margin: '0 0 8px 0', paddingLeft: '20px' }}>{children}</ol>,
                      li: ({ children }) => <li style={{ marginBottom: '4px' }}>{children}</li>,
                      h1: ({ children }) => <h1 style={{ fontSize: '18px', fontWeight: '700', margin: '12px 0 8px 0', color: 'var(--astrovox-text)' }}>{children}</h1>,
                      h2: ({ children }) => <h2 style={{ fontSize: '16px', fontWeight: '600', margin: '10px 0 6px 0', color: 'var(--astrovox-text)' }}>{children}</h2>,
                      h3: ({ children }) => <h3 style={{ fontSize: '14px', fontWeight: '600', margin: '8px 0 4px 0', color: 'var(--astrovox-text)' }}>{children}</h3>,
                      blockquote: ({ children }) => <blockquote style={{ borderLeft: '3px solid var(--astrovox-primary)', paddingLeft: '12px', margin: '8px 0', color: 'var(--astrovox-text-muted)' }}>{children}</blockquote>,
                      a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--astrovox-primary)', textDecoration: 'none' }}>{children}</a>,
                      table: ({ children }) => <div style={{ overflowX: 'auto', margin: '8px 0' }}><table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '13px' }}>{children}</table></div>,
                      th: ({ children }) => <th style={{ border: '1px solid var(--astrovox-border)', padding: '8px', background: 'var(--astrovox-surface)', textAlign: 'left' }}>{children}</th>,
                      td: ({ children }) => <td style={{ border: '1px solid var(--astrovox-border)', padding: '8px' }}>{children}</td>,
                      code: ({ inline, children, className }) => {
                        if (inline) {
                          return <code style={{ background: 'var(--astrovox-surface-hover)', padding: '2px 6px', borderRadius: '4px', fontFamily: 'var(--astrovox-font-mono)', fontSize: '12px' }}>{children}</code>
                        }
                        return <code className={className}>{children}</code>
                      },
                      pre: ({ children }) => <div style={{ marginTop: '10px' }}>{children}</div>,
                      strong: ({ children }) => <strong style={{ fontWeight: '600' }}>{children}</strong>,
                      em: ({ children }) => <em>{children}</em>,
                      hr: () => <hr style={{ border: 'none', borderTop: '1px solid var(--astrovox-border)', margin: '12px 0' }} />
                    }}
                  >
                    {block.content}
                  </ReactMarkdown>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
