import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function VoiceInput({ onTranscript, isListening, onToggleListening }) {
  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const [error, setError] = useState(null)
  const recognitionRef = useRef(null)

  useEffect(() => {
    if (typeof window !== 'undefined' && 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = true
      recognitionRef.current.interimResults = true
      recognitionRef.current.lang = 'en-US'

      recognitionRef.current.onresult = (event) => {
        let finalTranscript = ''
        let interim = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript
          } else {
            interim += event.results[i][0].transcript
          }
        }
        setTranscript(finalTranscript)
        setInterimTranscript(interim)
        if (finalTranscript) {
          onTranscript?.(finalTranscript)
        }
      }

      recognitionRef.current.onerror = (event) => {
        setError(event.error)
        onToggleListening?.(false)
      }

      recognitionRef.current.onend = () => {
        onToggleListening?.(false)
      }
    } else {
      setError('Speech recognition not supported in this browser')
    }
  }, [onTranscript, onToggleListening])

  useEffect(() => {
    if (isListening && recognitionRef.current) {
      recognitionRef.current.start()
    } else if (!isListening && recognitionRef.current) {
      recognitionRef.current.stop()
    }
  }, [isListening])

  const toggleListening = useCallback(() => {
    onToggleListening?.(!isListening)
    setTranscript('')
    setInterimTranscript('')
    setError(null)
  }, [isListening, onToggleListening])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <motion.button
          onClick={toggleListening}
          style={{
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            backgroundColor: isListening ? 'var(--astrovox-error)' : 'var(--astrovox-primary)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--astrovox-bg)'
          }}
          whileTap={{ scale: 0.95 }}
          animate={isListening ? { scale: [1, 1.1, 1] } : {}}
          transition={{ duration: 1.5, repeat: Infinity }}
          aria-label={isListening ? 'Stop listening' : 'Start listening'}
        >
          <Icon name="mic" size={20} />
        </motion.button>
        <div style={{ flex: 1 }}>
          {isListening ? (
            <div style={{ fontSize: '12px', color: 'var(--astrovox-success)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ display: 'flex', gap: '3px' }}>
                <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 0.6, repeat: Infinity }} style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--astrovox-success)' }} />
                <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }} style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--astrovox-success)' }} />
                <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }} style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--astrovox-success)' }} />
              </div>
              Listening...
            </div>
          ) : (
            <span style={{ fontSize: '12px', color: 'var(--astrovox-text-muted)' }}>Click to start voice input</span>
          )}
        </div>
      </div>

      {(transcript || interimTranscript) && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-md)',
            fontSize: '12px',
            color: 'var(--astrovox-text)',
            fontStyle: interimTranscript ? 'italic' : 'normal'
          }}
        >
          {transcript}
          {interimTranscript && <span style={{ color: 'var(--astrovox-text-muted)' }}>{interimTranscript}</span>}
        </div>
      )}

      {error && (
        <div
          style={{
            padding: '8px 12px',
            backgroundColor: 'var(--astrovox-error-bg)',
            border: '1px solid var(--astrovox-error)',
            borderRadius: 'var(--astrovox-radius-md)',
            color: 'var(--astrovox-error)',
            fontSize: '11px'
          }}
        >
          {error}
        </div>
      )}
    </div>
  )
}
