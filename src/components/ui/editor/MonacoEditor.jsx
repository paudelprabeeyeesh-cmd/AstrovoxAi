import { useEffect, useRef, useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../../design/Iconography.jsx'
import { useA11y } from '../A11yProvider'

export function MonacoEditor({
  value = '',
  language = 'javascript',
  theme = 'vs-dark',
  onChange,
  readOnly = false,
  height = '300px',
  minimap = true,
  lineNumbers = 'on'
}) {
  const containerRef = useRef(null)
  const editorRef = useRef(null)
  const [isReady, setIsReady] = useState(false)
  const [error, setError] = useState(null)
  const { announce } = useA11y()

  const monacoRef = useRef(null)

  const loadMonaco = useCallback(async () => {
    if (editorRef.current) return
    try {
      const monaco = await import('monaco-editor')
      monacoRef.current = monaco
      editorRef.current = monaco.editor.create(containerRef.current, {
        value,
        language,
        theme,
        readOnly,
        minimap: { enabled: minimap },
        lineNumbers,
        fontSize: 13,
        fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace",
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 2,
        wordWrap: 'on',
        padding: { top: 12, bottom: 12 }
      })

      editorRef.current.onDidChangeModelContent(() => {
        const newValue = editorRef.current.getValue()
        onChange?.(newValue)
      })

      setIsReady(true)
      setError(null)
      announce(`Code editor loaded for ${language}`)
    } catch (err) {
      setError('Failed to load code editor')
      console.error(err)
    }
  }, [value, language, theme, readOnly, minimap, lineNumbers, onChange, announce])

  useEffect(() => {
    loadMonaco()
    return () => {
      if (editorRef.current) {
        editorRef.current.dispose()
        editorRef.current = null
      }
    }
  }, [loadMonaco])

  useEffect(() => {
    if (!editorRef.current || !isReady) return
    const model = editorRef.current.getModel()
    if (model && monacoRef.current) {
      monacoRef.current.editor.setModelLanguage(model, language)
    }
  }, [language, isReady])

  useEffect(() => {
    if (!editorRef.current || !isReady) return
    const currentValue = editorRef.current.getValue()
    if (currentValue !== value) {
      editorRef.current.setValue(value)
    }
  }, [value, isReady])

  if (error) {
    return (
      <div
        style={{
          height,
          border: '1px solid var(--astrovox-error)',
          borderRadius: 'var(--astrovox-radius-lg)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--astrovox-error)',
          fontSize: '12px'
        }}
      >
        <Icon name="alert" size={16} style={{ marginRight: '8px' }} />
        {error}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        height,
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        overflow: 'hidden',
        position: 'relative'
      }}
    >
      {!isReady && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--astrovox-surface)',
            zIndex: 10
          }}
        >
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
        </div>
      )}
      <div
        ref={containerRef}
        style={{ height: '100%', width: '100%' }}
        role="textbox"
        aria-multiline="true"
        aria-label={`Code editor, ${language}`}
        tabIndex={readOnly ? -1 : 0}
      />
    </motion.div>
  )
}
