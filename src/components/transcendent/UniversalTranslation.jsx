import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { translateText, getSupportedLanguages } from '../../services/translationService'

export default function UniversalTranslation({ text = '', onTranslated }) {
  const [sourceLang, setSourceLang] = useState('en')
  const [targetLang, setTargetLang] = useState('es')
  const [translated, setTranslated] = useState('')
  const [languages, setLanguages] = useState([])
  const [isTranslating, setIsTranslating] = useState(false)

  useEffect(() => {
    getSupportedLanguages().then(data => {
      setLanguages(data.languages || [])
    })
  }, [])

  useEffect(() => {
    if (!text.trim()) {
      setTranslated('')
      return
    }
    const timer = setTimeout(async () => {
      setIsTranslating(true)
      try {
        const data = await translateText(text, sourceLang, targetLang)
        setTranslated(data.target_text)
        onTranslated?.(data)
      } catch (e) {
        console.error('Translation failed:', e)
      } finally {
        setIsTranslating(false)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [text, sourceLang, targetLang, onTranslated])

  if (!text) return null

  return (
    <div style={{
      position: 'fixed',
      top: '16px',
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 9999,
      backgroundColor: 'rgba(4, 8, 20, 0.9)',
      border: '1px solid #22c55e',
      borderRadius: '12px',
      padding: '12px 16px',
      minWidth: '400px',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <span style={{ fontSize: '14px', color: '#22c55e' }}>🌐</span>
        <span style={{ fontSize: '11px', color: '#22c55e', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>
          Universal Translation
        </span>
        <select
          value={sourceLang}
          onChange={(e) => setSourceLang(e.target.value)}
          style={{
            marginLeft: 'auto',
            background: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            color: 'var(--astrovox-text)',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '10px'
          }}
        >
          {languages.map(lang => (
            <option key={lang} value={lang}>{lang.toUpperCase()}</option>
          ))}
        </select>
        <span style={{ color: '#64748b' }}>→</span>
        <select
          value={targetLang}
          onChange={(e) => setTargetLang(e.target.value)}
          style={{
            background: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            color: 'var(--astrovox-text)',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '10px'
          }}
        >
          {languages.map(lang => (
            <option key={lang} value={lang}>{lang.toUpperCase()}</option>
          ))}
        </select>
      </div>
      <motion.div
        key={translated}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{
          padding: '8px 12px',
          backgroundColor: 'rgba(34,197,94,0.05)',
          borderRadius: '6px',
          fontSize: '12px',
          color: '#e2e8f0',
          minHeight: '32px'
        }}
      >
        {isTranslating ? 'Translating...' : translated || 'Waiting for text...'}
      </motion.div>
    </div>
  )
}
