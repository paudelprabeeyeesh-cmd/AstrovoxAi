import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'
import { useMathAndDiagrams } from '../../utils/mathAndDiagrams'

export default function MermaidBlock({ content }) {
  useMathAndDiagrams()
  const containerRef = useRef(null)
  const [svg, setSvg] = useState(null)
  const [error, setError] = useState(null)
  const [mermaidLib, setMermaidLib] = useState(null)

  useEffect(() => {
    const loadMermaid = async () => {
      try {
        if (typeof window !== 'undefined' && window.mermaid) {
          setMermaidLib(window.mermaid)
        } else {
          const mermaid = await import('mermaid')
          const lib = mermaid.default || mermaid
          setMermaidLib(lib)
        }
      } catch (err) {
        setError('Mermaid library not available')
      }
    }
    loadMermaid()
  }, [])

  useEffect(() => {
    if (!mermaidLib || !content) return
    let cancelled = false

    const renderDiagram = async () => {
      try {
        if (!mermaidLib.initialized) {
          mermaidLib.initialize({
            startOnLoad: false,
            theme: 'dark',
            securityLevel: 'loose'
          })
          mermaidLib.initialized = true
        }
        const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        const { svg: renderedSvg } = await mermaidLib.render(id, content)
        if (!cancelled) {
          setSvg(renderedSvg)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to render diagram')
          setSvg(null)
        }
      }
    }

    renderDiagram()
    return () => { cancelled = true }
  }, [content, mermaidLib])

  if (error) {
    return (
      <div
        style={{
          padding: '16px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--astrovox-error)',
          borderRadius: 'var(--astrovox-radius-md)',
          fontSize: '12px',
          color: 'var(--astrovox-error)'
        }}
      >
        <Icon name="alert" size={14} style={{ marginRight: '6px' }} />
        Diagram error: {error}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        padding: '16px',
        backgroundColor: 'var(--astrovox-code)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        overflowX: 'auto',
        textAlign: 'center'
      }}
    >
      {svg ? (
        <div
          ref={containerRef}
          dangerouslySetInnerHTML={{ __html: svg }}
          style={{
            display: 'flex',
            justifyContent: 'center',
            color: 'var(--astrovox-text)'
          }}
        />
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '20px' }}>
          <div
            style={{
              width: '20px',
              height: '20px',
              border: '2px solid var(--astrovox-primary)',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }}
          />
          <span style={{ fontSize: '12px', color: 'var(--astrovox-text-muted)' }}>Rendering diagram...</span>
        </div>
      )}
    </motion.div>
  )
}
