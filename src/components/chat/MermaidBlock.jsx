import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function MermaidBlock({ content }) {
  const containerRef = useRef(null)
  const [svg, setSvg] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        if (typeof window !== 'undefined' && window.mermaid) {
          const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
          const { svg: renderedSvg } = await window.mermaid.render(id, content)
          setSvg(renderedSvg)
        }
      } catch (err) {
        setError(err.message || 'Failed to render diagram')
      }
    }
    renderDiagram()
  }, [content])

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
