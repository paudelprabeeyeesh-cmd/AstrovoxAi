import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function VoiceOutput({ text, voice = 'default', rate = 1, pitch = 1 }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const utteranceRef = useRef(null)

  useEffect(() => {
    if (!text || typeof window === 'undefined' || !window.speechSynthesis) return

    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.voice = window.speechSynthesis.getVoices().find(v => v.name.includes(voice)) || null
    utterance.rate = rate
    utterance.pitch = pitch

    utterance.onstart = () => { setIsPlaying(true); setIsPaused(false) }
    utterance.onend = () => { setIsPlaying(false); setIsPaused(false) }
    utterance.onerror = () => { setIsPlaying(false); setIsPaused(false) }

    utteranceRef.current = utterance
    return () => { window.speechSynthesis.cancel() }
  }, [text, voice, rate, pitch])

  const togglePlay = useCallback(() => {
    if (!window.speechSynthesis) return
    if (isPlaying) {
      if (isPaused) {
        window.speechSynthesis.resume()
        setIsPaused(false)
      } else {
        window.speechSynthesis.pause()
        setIsPaused(true)
      }
    } else {
      if (utteranceRef.current) {
        window.speechSynthesis.speak(utteranceRef.current)
      }
    }
  }, [isPlaying, isPaused])

  const stop = useCallback(() => {
    window.speechSynthesis.cancel()
    setIsPlaying(false)
    setIsPaused(false)
  }, [])

  if (!text || typeof window === 'undefined' || !window.speechSynthesis) return null

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px 12px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-md)'
      }}
    >
      <motion.button
        onClick={togglePlay}
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          backgroundColor: isPlaying ? 'var(--astrovox-warning)' : 'var(--astrovox-primary)',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--astrovox-bg)'
        }}
        whileTap={{ scale: 0.95 }}
        aria-label={isPlaying ? (isPaused ? 'Resume' : 'Pause') : 'Play'}
      >
        {isPlaying && !isPaused ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <rect x="6" y="4" width="4" height="16" />
            <rect x="14" y="4" width="4" height="16" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
        )}
      </motion.button>
      {isPlaying && (
        <button
          onClick={stop}
          style={{
            background: 'transparent',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)',
            padding: '4px 8px',
            color: 'var(--astrovox-text-muted)',
            cursor: 'pointer',
            fontSize: '10px',
            fontFamily: 'inherit'
          }}
          aria-label="Stop"
        >
          Stop
        </button>
      )}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '11px', color: 'var(--astrovox-text)', fontWeight: '500' }}>
          {isPlaying ? (isPaused ? 'Paused' : 'Playing...') : 'Text to Speech'}
        </div>
        <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>
          {isPlaying ? 'Speaking' : 'Click play to hear'}
        </div>
      </div>
      <Icon name="audio" size={20} style={{ color: 'var(--astrovox-primary)', opacity: isPlaying ? 1 : 0.5 }} />
    </div>
  )
}
