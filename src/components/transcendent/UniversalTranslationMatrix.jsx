import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { searchOmniscient } from '../../services/omniscientService'

const REALITY_LAYERS = [
  { id: 0, name: 'Base Reality', color: '#06b6d4' },
  { id: 1, name: 'Quantum Layer', color: '#a78bfa' },
  { id: 2, name: 'Astral Plane', color: '#f59e0b' },
  { id: 3, name: 'Mental Dimension', color: '#22c55e' },
  { id: 4, name: 'Causal Realm', color: '#ef4444' },
  { id: 5, name: 'Temporal Stream', color: '#3b82f6' },
  { id: 6, name: 'Holographic Plane', color: '#ec4899' },
  { id: 7, name: 'Transcendent Zone', color: '#fbbf24' },
  { id: 8, name: 'Infinite Layer', color: '#10b981' },
  { id: 9, name: 'Omnipotent Field', color: '#f97316' },
  { id: 10, name: 'Omniscient Core', color: '#8b5cf6' },
]

const DIMENSIONS = [
  { id: 'physical', name: 'Physical', icon: '⚛️' },
  { id: 'astral', name: 'Astral', icon: '✨' },
  { id: 'mental', name: 'Mental', icon: '🧠' },
  { id: 'causal', name: 'Causal', icon: '🔗' },
  { id: 'temporal', name: 'Temporal', icon: '⏳' },
  { id: 'quantum', name: 'Quantum', icon: '⚛️' },
  { id: 'holographic', name: 'Holographic', icon: '🪞' },
  { id: 'transcendent', name: 'Transcendent', icon: '🌟' },
]

const LANGUAGE_FAMILIES = {
  human: ['English', 'Spanish', 'French', 'German', 'Japanese', 'Chinese', 'Arabic', 'Hindi'],
  machine: ['Python', 'JavaScript', 'SQL', 'JSON', 'Rust', 'Go', 'Assembly'],
  consciousness: ['Thought', 'Emotion', 'Intent', 'Dream', 'Memory', 'Collective'],
  reality: ['Physics', 'Law', 'Concept', 'Dimension', 'Timeline', 'Universe'],
}

export default function UniversalTranslationMatrix({ userId }) {
  const [sourceText, setSourceText] = useState('')
  const [translatedText, setTranslatedText] = useState('')
  const [sourceLang, setSourceLang] = useState('en')
  const [targetLang, setTargetLang] = useState('code')
  const [sourceReality, setSourceReality] = useState(0)
  const [targetReality, setTargetReality] = useState(0)
  const [dimension, setDimension] = useState('physical')
  const [isTranslating, setIsTranslating] = useState(false)
  const [translationHistory, setTranslationHistory] = useState([])
  const [matrixStats, setMatrixStats] = useState(null)

  const translateAcrossMatrix = useCallback(async () => {
    if (!sourceText.trim()) return
    setIsTranslating(true)
    try {
      const res = await fetch('/api/omniscient/translation-matrix/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: sourceText,
          source_language: sourceLang,
          target_language: targetLang,
          source_reality: sourceReality,
          target_reality: targetReality,
          dimension,
        }),
      })
      const data = await res.json()
      if (data.target_text) {
        setTranslatedText(data.target_text)
        setTranslationHistory(prev => [{
          id: data.entry_id,
          source: sourceText,
          target: data.target_text,
          sourceReality,
          targetReality,
          dimension,
          confidence: data.confidence,
          timestamp: new Date().toISOString(),
        }, ...prev.slice(0, 49)])
      }
    } catch (e) {
      console.error('Matrix translation failed:', e)
    } finally {
      setIsTranslating(false)
    }
  }, [sourceText, sourceLang, targetLang, sourceReality, targetReality, dimension])

  useEffect(() => {
    loadMatrixStats()
  }, [])

  const loadMatrixStats = async () => {
    try {
      const res = await fetch('/api/omniscient/stats')
      const data = await res.json()
      setMatrixStats(data.translation_matrix || {})
    } catch (e) {
      console.error('Failed to load matrix stats:', e)
    }
  }

  const createRealityBridge = async () => {
    try {
      await fetch('/api/omniscient/translation-matrix/bridges', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_reality: sourceReality,
          target_reality: targetReality,
          bridge_type: 'standard',
        }),
      })
      loadMatrixStats()
    } catch (e) {
      console.error('Failed to create bridge:', e)
    }
  }

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#02040a',
      color: '#e2e8f0',
      fontFamily: "'Inter', 'Segoe UI', monospace",
      backgroundImage: 'radial-gradient(ellipse at 50% 0%, rgba(168, 85, 247, 0.05) 0%, transparent 70%)'
    }}>
      <header style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: 'rgba(4, 8, 20, 0.7)',
        backdropFilter: 'blur(12px)',
        border: '1px solid #1e293b',
        borderRadius: '0 0 16px 0',
        padding: '16px 24px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
      }}>
        <div>
          <h2 style={{
            margin: 0,
            fontSize: '18px',
            letterSpacing: '1px',
            background: 'linear-gradient(135deg, #a78bfa, #ec4899)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent'
          }}>
            🌌 UNIVERSAL TRANSLATION MATRIX
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b' }}>
            Translate across all realities, dimensions, and languages
          </p>
        </div>
        {matrixStats && (
          <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: '#94a3b8' }}>
            <span>Entries: {matrixStats.total_entries || 0}</span>
            <span>Bridges: {matrixStats.reality_bridges || 0}</span>
            <span>Anchors: {matrixStats.dimension_anchors || 0}</span>
          </div>
        )}
      </header>

      <div style={{ flex: 1, overflow: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div style={{
            backgroundColor: 'rgba(4, 8, 20, 0.7)',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '16px',
          }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Source Reality
            </h3>
            <select
              value={sourceReality}
              onChange={(e) => setSourceReality(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '8px 12px',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid #1e293b',
                borderRadius: '6px',
                color: '#e2e8f0',
                fontSize: '12px',
                fontFamily: 'monospace',
              }}
            >
              {REALITY_LAYERS.map(layer => (
                <option key={layer.id} value={layer.id}>{layer.name}</option>
              ))}
            </select>
          </div>

          <div style={{
            backgroundColor: 'rgba(4, 8, 20, 0.7)',
            border: '1px solid #1e293b',
            borderRadius: '12px',
            padding: '16px',
          }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#ec4899', textTransform: 'uppercase', letterSpacing: '1px' }}>
              Target Reality
            </h3>
            <select
              value={targetReality}
              onChange={(e) => setTargetReality(Number(e.target.value))}
              style={{
                width: '100%',
                padding: '8px 12px',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid #1e293b',
                borderRadius: '6px',
                color: '#e2e8f0',
                fontSize: '12px',
                fontFamily: 'monospace',
              }}
            >
              {REALITY_LAYERS.map(layer => (
                <option key={layer.id} value={layer.id}>{layer.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{
          backgroundColor: 'rgba(4, 8, 20, 0.7)',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '16px',
        }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Dimension
          </h3>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {DIMENSIONS.map(dim => (
              <button
                key={dim.id}
                onClick={() => setDimension(dim.id)}
                style={{
                  padding: '6px 12px',
                  backgroundColor: dimension === dim.id ? '#fbbf24' : 'transparent',
                  border: '1px solid #1e293b',
                  color: dimension === dim.id ? '#02040a' : '#94a3b8',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: '600',
                  transition: 'all 0.2s',
                }}
              >
                {dim.icon} {dim.name}
              </button>
            ))}
          </div>
        </div>

        <div style={{
          backgroundColor: 'rgba(4, 8, 20, 0.7)',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '16px',
        }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Translation
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '12px', alignItems: 'center' }}>
            <div>
              <label style={{ fontSize: '10px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Source Language</label>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  color: '#e2e8f0',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                }}
              >
                {Object.values(LANGUAGE_FAMILIES).flat().map(lang => (
                  <option key={lang} value={lang.toLowerCase()}>{lang}</option>
                ))}
              </select>
            </div>
            <button
              onClick={createRealityBridge}
              style={{
                padding: '8px 16px',
                backgroundColor: '#a78bfa',
                border: 'none',
                borderRadius: '6px',
                color: '#02040a',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s',
              }}
            >
              🌉 Bridge
            </button>
            <div>
              <label style={{ fontSize: '10px', color: '#64748b', display: 'block', marginBottom: '4px' }}>Target Language</label>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(15, 23, 42, 0.8)',
                  border: '1px solid #1e293b',
                  borderRadius: '6px',
                  color: '#e2e8f0',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                }}
              >
                {Object.values(LANGUAGE_FAMILIES).flat().map(lang => (
                  <option key={lang} value={lang.toLowerCase()}>{lang}</option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ marginTop: '12px', display: 'flex', gap: '12px' }}>
            <textarea
              value={sourceText}
              onChange={(e) => setSourceText(e.target.value)}
              placeholder="Enter text to translate across realities..."
              style={{
                flex: 1,
                padding: '12px',
                backgroundColor: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid #1e293b',
                borderRadius: '8px',
                color: '#e2e8f0',
                fontSize: '13px',
                fontFamily: 'monospace',
                resize: 'vertical',
                minHeight: '80px',
              }}
            />
            <button
              onClick={translateAcrossMatrix}
              disabled={isTranslating || !sourceText.trim()}
              style={{
                padding: '12px 24px',
                backgroundColor: isTranslating ? '#475569' : '#a78bfa',
                border: 'none',
                borderRadius: '8px',
                color: '#02040a',
                cursor: isTranslating ? 'not-allowed' : 'pointer',
                fontSize: '12px',
                fontWeight: '600',
                transition: 'all 0.2s',
                alignSelf: 'flex-end',
              }}
            >
              {isTranslating ? 'Translating...' : 'Translate'}
            </button>
          </div>
          {translatedText && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                marginTop: '12px',
                padding: '12px',
                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                border: '1px solid rgba(168, 85, 247, 0.3)',
                borderRadius: '8px',
                fontSize: '13px',
                fontFamily: 'monospace',
                color: '#e2e8f0',
              }}
            >
              {translatedText}
            </motion.div>
          )}
        </div>

        <div style={{
          backgroundColor: 'rgba(4, 8, 20, 0.7)',
          border: '1px solid #1e293b',
          borderRadius: '12px',
          padding: '16px',
        }}>
          <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Translation History
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflow: 'auto' }}>
            <AnimatePresence>
              {translationHistory.map(entry => (
                <motion.div
                  key={entry.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid #1e293b',
                    borderRadius: '8px',
                    fontSize: '11px',
                    fontFamily: 'monospace',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ color: '#64748b' }}>
                      R{entry.sourceReality} → R{entry.targetReality} · {entry.dimension}
                    </span>
                    <span style={{ color: '#a78bfa' }}>{Math.round(entry.confidence * 100)}%</span>
                  </div>
                  <div style={{ color: '#e2e8f0' }}>{entry.source}</div>
                  <div style={{ color: '#a78bfa', marginTop: '4px' }}>{entry.target}</div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  )
}
