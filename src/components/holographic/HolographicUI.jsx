import { useRef, useEffect, useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'
import { useWebGLHolographicRenderer } from '../../hooks/holographic/useWebGLHolographicRenderer'
import { useGestureRecognizer } from '../../hooks/holographic/useGestureRecognition'
import { useDepthAwareInteractions } from '../../hooks/holographic/useDepthAwareInteractions'

export function HolographicCanvas({ children, className = '', style = {}, interactive = true, depthEnabled = true }) {
  const containerRef = useRef(null)
  const [isHovered, setIsHovered] = useState(false)
  const [gestureState, setGestureState] = useState({ type: null, progress: 0 })
  const { canvasRef, render, startRenderLoop, stopRenderLoop } = useWebGLHolographicRenderer()
  const { gesture, confidence, isTracking, startTracking, stopTracking, addPoint } = useGestureRecognizer()
  const { depthMap, updateDepth, calculateParallax, focusOnElement, blurElement, focusedElement } = useDepthAwareInteractions()

  const renderParams = useCallback(() => ({
    mouse: [0.5, 0.5],
    hoverIntensity: isHovered ? 1 : 0,
    gestureProgress: gestureState.progress,
    gestureType: gestureState.type === 'swipe' ? 1 : gestureState.type === 'pinch' ? 2 : gestureState.type === 'rotate' ? 3 : 0,
    depth: focusedElement?.depth || 0.5,
    persistence: HOLOGRAPHIC_CONFIG.hologram.persistence,
    diffraction: HOLOGRAPHIC_CONFIG.hologram.diffraction,
    interference: HOLOGRAPHIC_CONFIG.hologram.interference,
    chromaticAberration: HOLOGRAPHIC_CONFIG.glitch.chromaticAberration,
    scanlineOpacity: HOLOGRAPHIC_CONFIG.glitch.scanlineOpacity,
    noiseAmount: HOLOGRAPHIC_CONFIG.glitch.noiseAmount,
    glitchIntensity: isHovered ? 0.1 : 0
  }), [isHovered, gestureState, focusedElement])

  useEffect(() => {
    startRenderLoop(renderParams)
    return () => stopRenderLoop()
  }, [startRenderLoop, stopRenderLoop, renderParams])

  const handleMouseMove = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = 1 - (e.clientY - rect.top) / rect.height

    if (interactive) {
      addPoint(x, y)
    }
  }, [addPoint, interactive])

  const handleMouseEnter = useCallback(() => {
    setIsHovered(true)
    if (interactive) {
      startTracking()
    }
  }, [startTracking, interactive])

  const handleMouseLeave = useCallback(() => {
    setIsHovered(false)
    stopTracking()
  }, [stopTracking])

  useEffect(() => {
    if (gesture) {
      setGestureState({ type: gesture, progress: confidence })
      setTimeout(() => {
        setGestureState({ type: null, progress: 0 })
      }, HOLOGRAPHIC_CONFIG.gesture.recognitionWindow)
    }
  }, [gesture, confidence])

  return (
    <div
      ref={containerRef}
      className={className}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        perspective: '1000px',
        transformStyle: 'preserve-3d',
        ...style
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 0
        }}
      />
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          transformStyle: 'preserve-3d',
          transition: 'transform 0.1s ease-out'
        }}
      >
        {typeof children === 'function' ? children({ isHovered, gesture, confidence }) : children}
      </div>
    </div>
  )
}

export function VolumetricDisplay({ width = 32, height = 32, depth = 32, active = true, className = '', style = {} }) {
  const canvasRef = useRef(null)
  const { voxels, isActive, density, emission, rotation, startVolumetricDisplay, stopVolumetricDisplay, initializeGrid, updateRotation } = useVolumetricDisplay()
  const [localRotation, setLocalRotation] = useState({ x: 0, y: 0, z: 0 })

  useEffect(() => {
    if (active) {
      startVolumetricDisplay({ width, height, depth })
    } else {
      stopVolumetricDisplay()
    }

    return () => stopVolumetricDisplay()
  }, [active, width, height, depth, startVolumetricDisplay, stopVolumetricDisplay])

  useEffect(() => {
    const handleMouseMove = (e) => {
      const rect = canvasRef.current?.getBoundingClientRect()
      if (!rect) return

      const x = (e.clientX - rect.left) / rect.width - 0.5
      const y = (e.clientY - rect.top) / rect.height - 0.5

      setLocalRotation({
        x: y * 0.5,
        y: x * 0.5,
        z: 0
      })
    }

    const canvas = canvasRef.current
    if (canvas) {
      canvas.addEventListener('mousemove', handleMouseMove)
      return () => canvas.removeEventListener('mousemove', handleMouseMove)
    }
  }, [])

  useEffect(() => {
    updateRotation(localRotation.x, localRotation.y, localRotation.z)
  }, [localRotation, updateRotation])

  return (
    <div
      ref={canvasRef}
      className={className}
      style={{
        position: 'relative',
        width: '100%',
        height: '400px',
        overflow: 'hidden',
        background: 'transparent',
        perspective: '1000px',
        transformStyle: 'preserve-3d',
        ...style
      }}
    >
      <div style={{
        position: 'absolute',
        inset: 0,
        transformStyle: 'preserve-3d',
        transform: `rotateX(${localRotation.x * 20}deg) rotateY(${localRotation.y * 20}deg)`,
        transition: 'transform 0.1s ease-out'
      }}>
        {voxels.map((voxel, index) => (
          <div
            key={index}
            style={{
              position: 'absolute',
              left: voxel.x,
              top: voxel.y,
              width: voxel.size,
              height: voxel.size,
              backgroundColor: voxel.color,
              opacity: voxel.opacity,
              borderRadius: '50%',
              transform: `translateZ(${voxel.z * 10}px)`,
              boxShadow: `0 0 ${voxel.size * 1.5}px ${voxel.color}`,
              pointerEvents: 'none',
              transformStyle: 'preserve-3d'
            }}
          />
        ))}
      </div>
    </div>
  )
}

export function HolographicChatInterface({ messages = [], onSendMessage, className = '', style = {} }) {
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const { gesture, confidence, gestureHistory } = useGestureRecognizer()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (gesture === 'swipe' && confidence > 0.7) {
      inputRef.current?.focus()
    }
  }, [gesture, confidence])

  const handleSend = useCallback((e) => {
    e?.preventDefault()
    if (!input.trim()) return

    onSendMessage?.(input.trim())
    setInput('')
  }, [input, onSendMessage])

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.floatingPanel,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
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
        <div>
          <h3 style={{ margin: 0, color: HOLOGRAPHIC_COLORS.accent, fontSize: '14px', fontWeight: 600 }}>
            Holographic Interface
          </h3>
          <p style={{ margin: 0, color: 'var(--astrovox-text-muted)', fontSize: '12px' }}>
            Neural link active
          </p>
        </div>
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
        {isTyping && (
          <div style={{
            alignSelf: 'flex-start',
            padding: '12px 16px',
            borderRadius: '12px',
            background: HOLOGRAPHIC_LAYOUTS.hologramCard.background,
            border: HOLOGRAPHIC_LAYOUTS.hologramCard.border,
            display: 'flex',
            gap: '4px'
          }}>
            {[0, 1, 2].map(i => (
              <motion.div
                key={i}
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: HOLOGRAPHIC_COLORS.primary
                }}
              />
            ))}
          </div>
        )}
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
          placeholder="Send message via neural link..."
          style={{
            ...HOLOGRAPHIC_LAYOUTS.hologramInput,
            flex: 1,
            padding: '12px 16px',
            fontSize: '14px'
          }}
        />
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

export function FloatingPanel({ children, title, className = '', style = {}, depth = 0.5, draggable = true }) {
  const { updateDepth, calculateParallax } = useDepthAwareInteractions()
  const [position, setPosition] = useState({ x: 100, y: 100 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  useEffect(() => {
    updateDepth(`panel-${title || 'unnamed'}`, depth)
  }, [depth, title, updateDepth])

  const handleMouseDown = useCallback((e) => {
    if (!draggable) return
    setIsDragging(true)
    setDragStart({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    })
  }, [draggable, position])

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return
    setPosition({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    })
  }, [isDragging, dragStart])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
      return () => {
        window.removeEventListener('mousemove', handleMouseMove)
        window.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, handleMouseMove, handleMouseUp])

  const parallax = calculateParallax(depth, 0.5, 0.5)

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, scale: 0.9, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.9, y: 20 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      onMouseDown={handleMouseDown}
      style={{
        position: 'absolute',
        left: position.x,
        top: position.y,
        ...HOLOGRAPHIC_LAYOUTS.floatingPanel,
        transform: `perspective(1000px) rotateY(${parallax.rotationY}deg) rotateX(${parallax.rotationX}deg) translateX(${parallax.x}px) translateY(${parallax.y}px)`,
        cursor: draggable ? 'grab' : 'default',
        userSelect: 'none',
        ...style
      }}
    >
      {title && (
        <div style={{
          padding: '12px 16px',
          borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <h3 style={{
            margin: 0,
            color: HOLOGRAPHIC_COLORS.accent,
            fontSize: '14px',
            fontWeight: 600
          }}>
            {title}
          </h3>
          {draggable && (
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: HOLOGRAPHIC_COLORS.primary
            }} />
          )}
        </div>
      )}
      <div style={{ padding: '16px' }}>
        {children}
      </div>
    </motion.div>
  )
}

export function HolographicCard({ children, title, className = '', style = {}, onClick }) {
  return (
    <motion.div
      className={className}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        padding: '20px',
        cursor: onClick ? 'pointer' : 'default',
        ...style
      }}
    >
      {title && (
        <h3 style={{
          margin: '0 0 12px 0',
          color: HOLOGRAPHIC_COLORS.accent,
          fontSize: '16px',
          fontWeight: 600
        }}>
          {title}
        </h3>
      )}
      {children}
    </motion.div>
  )
}

export function HolographicButton({ children, variant = 'primary', size = 'md', className = '', style = {}, onClick, disabled }) {
  const sizeStyles = {
    sm: { padding: '8px 16px', fontSize: '12px' },
    md: { padding: '12px 24px', fontSize: '14px' },
    lg: { padding: '16px 32px', fontSize: '16px' }
  }

  const variantStyles = {
    primary: {
      background: `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.primary}30, ${HOLOGRAPHIC_COLORS.primary}20)`,
      border: `1px solid ${HOLOGRAPHIC_COLORS.primary}60`,
      color: HOLOGRAPHIC_COLORS.accent
    },
    secondary: {
      background: `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.secondary}30, ${HOLOGRAPHIC_COLORS.secondary}20)`,
      border: `1px solid ${HOLOGRAPHIC_COLORS.secondary}60`,
      color: HOLOGRAPHIC_COLORS.secondary
    },
    ghost: {
      background: 'transparent',
      border: `1px solid ${HOLOGRAPHIC_COLORS.primary}30`,
      color: HOLOGRAPHIC_COLORS.primary
    }
  }

  return (
    <motion.button
      className={className}
      whileHover={{ scale: 1.05, boxShadow: `0 0 20px ${HOLOGRAPHIC_COLORS.primary}30` }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      disabled={disabled}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramButton,
        ...sizeStyles[size],
        ...variantStyles[variant],
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        fontFamily: 'inherit',
        fontWeight: 500,
        ...style
      }}
    >
      {children}
    </motion.button>
  )
}
