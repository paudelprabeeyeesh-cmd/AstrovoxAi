import { useState, useEffect, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'
import { useWebXRIntegration } from '../../hooks/holographic/useWebXRIntegration'
import { useGestureRecognizer } from '../../hooks/holographic/useGestureRecognition'

export function WebXRChatExperience({ messages = [], onSendMessage, className = '', style = {} }) {
  const { isSupported, isInSession, startVRSession, endSession, handTracking, spatialAudio, haptics, mode } = useWebXRIntegration()
  const { gesture, confidence, startTracking, stopTracking } = useGestureRecognizer()
  const [input, setInput] = useState('')
  const [isVoiceActive, setIsVoiceActive] = useState(false)
  const [spatialPosition, setSpatialPosition] = useState({ x: 0, y: 1.6, z: -2 })
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const recognitionRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (gesture === 'swipe' && confidence > 0.7) {
      inputRef.current?.focus()
    }
    if (gesture === 'point' && confidence > 0.8) {
      handleSend()
    }
  }, [gesture, confidence])

  const startVoiceInput = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)()
      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = 'en-US'

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setInput(transcript)
        setIsVoiceActive(false)
      }

      recognition.onerror = () => {
        setIsVoiceActive(false)
      }

      recognition.onend = () => {
        setIsVoiceActive(false)
      }

      recognitionRef.current = recognition
      recognition.start()
      setIsVoiceActive(true)
    } catch (err) {
      console.error('Voice input failed:', err)
    }
  }, [])

  const stopVoiceInput = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setIsVoiceActive(false)
  }, [])

  const handleSend = useCallback((e) => {
    e?.preventDefault()
    const text = input.trim() || e?.target?.value?.trim()
    if (!text) return

    onSendMessage?.(text)
    setInput('')

    if (haptics) {
      haptics.vibrate('light')
    }
  }, [input, onSendMessage, haptics])

  const handleMouseMove = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = 1 - (e.clientY - rect.top) / rect.height

    if (isInSession) {
      setSpatialPosition({
        x: (x - 0.5) * 4,
        y: 1.6 + (y - 0.5) * 2,
        z: -2
      })
    }
  }, [isInSession])

  return (
    <div
      className={className}
      onMouseMove={handleMouseMove}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.floatingPanel,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        position: isInSession ? 'absolute' : 'relative',
        left: isInSession ? `${spatialPosition.x * 10}%` : 'auto',
        top: isInSession ? `${spatialPosition.y * 10}%` : 'auto',
        transform: isInSession
          ? `translateZ(${spatialPosition.z}m) rotateY(${(spatialPosition.x / 4) * 10}deg)`
          : 'none',
        ...style
      }}
    >
      <div style={{
        padding: '16px',
        borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          background: `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.primary}40, ${HOLOGRAPHIC_COLORS.secondary}40)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: `1px solid ${HOLOGRAPHIC_COLORS.primary}60`
        }}>
          <svg viewBox="0 0 24 24" fill="none" stroke={HOLOGRAPHIC_COLORS.accent} strokeWidth="2" width="20" height="20">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, color: HOLOGRAPHIC_COLORS.accent, fontSize: '14px', fontWeight: 600 }}>
            {isInSession ? `${mode.toUpperCase()} Chat` : 'Holographic Interface'}
          </h3>
          <p style={{ margin: 0, color: 'var(--astrovox-text-muted)', fontSize: '12px' }}>
            {isInSession ? 'Spatial voice active' : 'Neural link active'}
          </p>
        </div>
        {isInSession && handTracking && (
          <div style={{
            padding: '4px 8px',
            background: 'rgba(6, 182, 212, 0.1)',
            borderRadius: '4px',
            fontSize: '11px',
            color: HOLOGRAPHIC_COLORS.accent
          }}>
            {handTracking.joints?.length || 0} joints
          </div>
        )}
      </div>

      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px'
      }}>
        {messages.map((message, index) => (
          <motion.div
            key={message.id || index}
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
            style={{
              alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '75%',
              padding: '12px 16px',
              borderRadius: '12px',
              background: message.role === 'user'
                ? `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.primary}30, ${HOLOGRAPHIC_COLORS.primary}20)`
                : HOLOGRAPHIC_LAYOUTS.hologramCard.background,
              border: message.role === 'user'
                ? `1px solid ${HOLOGRAPHIC_COLORS.primary}60`
                : HOLOGRAPHIC_LAYOUTS.hologramCard.border,
              backdropFilter: 'blur(12px)',
              boxShadow: message.role === 'user'
                ? `0 0 20px ${HOLOGRAPHIC_COLORS.primary}20`
                : '0 4px 16px rgba(0, 0, 0, 0.3)'
            }}
          >
            <p style={{ margin: 0, color: 'var(--astrovox-text)', fontSize: '14px', lineHeight: 1.5 }}>
              {message.content}
            </p>
          </motion.div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSend} style={{
        padding: '16px',
        borderTop: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        gap: '12px'
      }}>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={isInSession ? 'Spatial message...' : 'Send message via neural link...'}
          style={{
            ...HOLOGRAPHIC_LAYOUTS.hologramInput,
            flex: 1,
            padding: '12px 16px',
            fontSize: '14px'
          }}
        />
        {isInSession && (
          <motion.button
            type="button"
            onClick={isVoiceActive ? stopVoiceInput : startVoiceInput}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            style={{
              ...HOLOGRAPHIC_LAYOUTS.hologramButton,
              padding: '12px 16px',
              background: isVoiceActive
                ? `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.error}40, ${HOLOGRAPHIC_COLORS.error}20)`
                : HOLOGRAPHIC_LAYOUTS.hologramButton.background,
              border: isVoiceActive
                ? `1px solid ${HOLOGRAPHIC_COLORS.error}60`
                : HOLOGRAPHIC_LAYOUTS.hologramButton.border,
              cursor: 'pointer'
            }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </motion.button>
        )}
        <motion.button
          type="submit"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          style={{
            ...HOLOGRAPHIC_LAYOUTS.hologramButton,
            padding: '12px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer'
          }}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
          <span style={{ fontSize: '14px' }}>Send</span>
        </motion.button>
      </form>
    </div>
  )
}
