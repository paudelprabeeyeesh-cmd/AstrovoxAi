import { useState, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../design/Iconography'

const SUPPORTED_LANGUAGES = [
  { id: 'javascript', label: 'JavaScript', ext: 'js' },
  { id: 'python', label: 'Python', ext: 'py' },
  { id: 'typescript', label: 'TypeScript', ext: 'ts' },
  { id: 'go', label: 'Go', ext: 'go' },
  { id: 'rust', label: 'Rust', ext: 'rs' },
  { id: 'bash', label: 'Bash', ext: 'sh' }
]

export default function CodeExecution({ onExecute, onClose }) {
  const [language, setLanguage] = useState('python')
  const [code, setCode] = useState('')
  const [output, setOutput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState(null)
  const textareaRef = useRef(null)

  const runCode = useCallback(async () => {
    if (!code.trim()) return
    setIsRunning(true)
    setError(null)
    setOutput('')

    try {
      const res = await fetch('/api/code/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language, code, timeout: 10000 })
      })
      if (!res.ok) throw new Error(`Execution failed with status ${res.status}`)
      const data = await res.json()
      setOutput(data.output || data.stdout || JSON.stringify(data, null, 2))
      onExecute?.(data)
    } catch (err) {
      setError(err.message)
      setOutput(err.message)
    } finally {
      setIsRunning(false)
    }
  }, [code, language, onExecute])

  const handleKeyDown = useCallback((e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      runCode()
    }
  }, [runCode])

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        padding: '16px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Icon name="play" size={18} style={{ color: 'var(--astrovox-primary)' }} />
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>Code Execution</h3>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{
              padding: '4px 8px',
              backgroundColor: 'var(--astrovox-bg)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-sm)',
              color: 'var(--astrovox-text)',
              fontSize: '12px',
              fontFamily: 'inherit'
            }}
          >
            {SUPPORTED_LANGUAGES.map(lang => (
              <option key={lang.id} value={lang.id}>{lang.label}</option>
            ))}
          </select>
          <button
            onClick={runCode}
            disabled={isRunning || !code.trim()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 12px',
              backgroundColor: isRunning ? 'var(--astrovox-surface-hover)' : 'var(--astrovox-primary)',
              color: isRunning ? 'var(--astrovox-text-muted)' : 'var(--astrovox-bg)',
              border: 'none',
              borderRadius: 'var(--astrovox-radius-sm)',
              fontSize: '12px',
              fontWeight: '600',
              cursor: isRunning ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit'
            }}
          >
            {isRunning ? 'Running...' : 'Run'}
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--astrovox-text-muted)',
              cursor: 'pointer',
              padding: '2px'
            }}
          >
            <Icon name="x" size={16} />
          </button>
        </div>
      </div>

      <textarea
        ref={textareaRef}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={`Write ${language} code here...`}
        spellCheck={false}
        style={{
          width: '100%',
          minHeight: '160px',
          padding: '12px',
          backgroundColor: 'var(--astrovox-bg)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-md)',
          color: 'var(--astrovox-code-text)',
          fontFamily: "var(--astrovox-font-mono)",
          fontSize: '13px',
          lineHeight: '1.5',
          resize: 'vertical',
          outline: 'none'
        }}
      />

      {(output || error) && (
        <div style={{
          padding: '12px',
          backgroundColor: error ? 'rgba(239, 68, 68, 0.05)' : 'var(--astrovox-bg)',
          border: `1px solid ${error ? 'var(--astrovox-error)' : 'var(--astrovox-border)'}`,
          borderRadius: 'var(--astrovox-radius-md)',
          maxHeight: '200px',
          overflowY: 'auto'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
            <Icon name={error ? 'alert-circle' : 'check-circle'} size={14} style={{ color: error ? 'var(--astrovox-error)' : 'var(--astrovox-success)' }} />
            <span style={{ fontSize: '11px', color: error ? 'var(--astrovox-error)' : 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: '600' }}>
              {error ? 'Error' : 'Output'}
            </span>
          </div>
          <pre style={{ margin: 0, fontSize: '12px', fontFamily: "var(--astrovox-font-mono)", color: 'var(--astrovox-text)', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {output}
          </pre>
        </div>
      )}
    </motion.div>
  )
}
