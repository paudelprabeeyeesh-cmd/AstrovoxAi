import { useState, useEffect, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'
import { useWebXRIntegration } from '../../hooks/holographic/useWebXRIntegration'
import { useGestureRecognizer } from '../../hooks/holographic/useGestureRecognizer'

export function VRWorkspace({ children, className = '', style = {} }) {
  const { isSupported, isInSession, startVRSession, endSession, handTracking, eyeTracking, haptics } = useWebXRIntegration()
  const canvasRef = useRef(null)
  const [vrReady, setVrReady] = useState(false)
  const [spatialPosition, setSpatialPosition] = useState({ x: 0, y: 1.6, z: 0 })
  const [headRotation, setHeadRotation] = useState({ x: 0, y: 0, z: 0 })

  useEffect(() => {
    if (isSupported) {
      setVrReady(true)
    }
  }, [isSupported])

  const enterVR = useCallback(async () => {
    const session = await startVRSession()
    if (session) {
      setVrReady(true)
    }
  }, [startVRSession])

  const exitVR = useCallback(async () => {
    await endSession()
    setVrReady(false)
  }, [endSession])

  const handleHandUpdate = useCallback((frame) => {
    if (handTracking && frame) {
      const positions = handTracking.joints?.map(joint => ({
        x: joint.position?.x || 0,
        y: joint.position?.y || 0,
        z: joint.position?.z || 0
      })) || []
      return positions
    }
    return []
  }, [handTracking])

  const handleEyeTracking = useCallback((gazeData) => {
    if (eyeTracking) {
      setSpatialPosition(prev => ({
        ...prev,
        x: gazeData.x || prev.x,
        y: gazeData.y || prev.y,
        z: gazeData.z || prev.z
      }))
    }
  }, [eyeTracking])

  const handleHapticFeedback = useCallback((pattern = 'medium', intensity = 1) => {
    haptics?.vibrate(pattern, intensity)
  }, [haptics])

  return (
    <div
      ref={canvasRef}
      className={className}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        perspective: '1000px',
        transformStyle: 'preserve-3d',
        ...style
      }}
    >
      {!isInSession && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '24px',
          background: 'rgba(2, 4, 10, 0.9)'
        }}>
          <div style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.primary}30, ${HOLOGRAPHIC_COLORS.secondary}30)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `2px solid ${HOLOGRAPHIC_COLORS.primary}60`,
            boxShadow: `0 0 30px ${HOLOGRAPHIC_COLORS.primary}40`
          }}>
            <svg viewBox="0 0 24 24" fill="none" stroke={HOLOGRAPHIC_COLORS.accent} strokeWidth="2" width="40" height="40">
              <path d="M2 7v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2z" />
              <polyline points="2 7 12 13 22 7" />
              <circle cx="12" cy="13" r="3" />
            </svg>
          </div>
          <div style={{ textAlign: 'center' }}>
            <h2 style={{ color: HOLOGRAPHIC_COLORS.accent, margin: '0 0 8px 0', fontSize: '20px' }}>
              VR Workspace
            </h2>
            <p style={{ color: 'var(--astrovox-text-muted)', margin: '0 0 24px 0', fontSize: '14px' }}>
              Immerse yourself in a 3D holographic environment
            </p>
            {vrReady ? (
              <motion.button
                onClick={enterVR}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                style={{
                  ...HOLOGRAPHIC_LAYOUTS.hologramButton,
                  padding: '16px 32px',
                  fontSize: '16px',
                  cursor: 'pointer'
                }}
              >
                Enter VR
              </motion.button>
            ) : (
              <p style={{ color: HOLOGRAPHIC_COLORS.warning, fontSize: '13px' }}>
                WebXR not supported on this device
              </p>
            )}
          </div>
        </div>
      )}
      {isInSession && (
        <div style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          right: '16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 16px',
          background: 'rgba(2, 4, 10, 0.7)',
          backdropFilter: 'blur(12px)',
          borderRadius: '8px',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          zIndex: 100
        }}>
          <div>
            <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '12px', fontWeight: 600 }}>
              VR ACTIVE
            </span>
            {handTracking && (
              <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px', marginLeft: '12px' }}>
                Hands: {handTracking.joints?.length || 0} joints
              </span>
            )}
          </div>
          <button
            onClick={exitVR}
            style={{
              padding: '8px 16px',
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid rgba(239, 68, 68, 0.5)',
              borderRadius: '6px',
              color: HOLOGRAPHIC_COLORS.error,
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Exit VR
          </button>
        </div>
      )}
      {children}
    </div>
  )
}

export function AROverlay({ className = '', style = {} }) {
  const { isSupported, startARSession, endSession, error } = useWebXRIntegration()
  const [arActive, setArActive] = useState(false)
  const [detectedObjects, setDetectedObjects] = useState([])
  const [overlayElements, setOverlayElements] = useState([])
  const canvasRef = useRef(null)

  const startAR = useCallback(async () => {
    const session = await startARSession()
    if (session) {
      setArActive(true)
    }
  }, [startARSession])

  const stopAR = useCallback(async () => {
    await endSession()
    setArActive(false)
    setDetectedObjects([])
  }, [endSession])

  const addOverlay = useCallback((element) => {
    setOverlayElements(prev => [...prev, {
      ...element,
      id: element.id || Date.now(),
      timestamp: Date.now()
    }])
  }, [])

  const removeOverlay = useCallback((id) => {
    setOverlayElements(prev => prev.filter(el => el.id !== id))
  }, [])

  const clearOverlays = useCallback(() => {
    setOverlayElements([])
  }, [])

  return (
    <div
      ref={canvasRef}
      className={className}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        ...style
      }}
    >
      {!arActive && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '16px'
        }}>
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.secondary}30, ${HOLOGRAPHIC_COLORS.primary}30)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `2px solid ${HOLOGRAPHIC_COLORS.secondary}60`
          }}>
            <svg viewBox="0 0 24 24" fill="none" stroke={HOLOGRAPHIC_COLORS.accent} strokeWidth="2" width="30" height="30">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
          </div>
          <p style={{ color: 'var(--astrovox-text-muted)', fontSize: '14px' }}>
            AR Overlay Ready
          </p>
          {isSupported ? (
            <motion.button
              onClick={startAR}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              style={{
                ...HOLOGRAPHIC_LAYOUTS.hologramButton,
                padding: '12px 24px',
                cursor: 'pointer'
              }}
            >
              Start AR
            </motion.button>
          ) : (
            <p style={{ color: HOLOGRAPHIC_COLORS.warning, fontSize: '13px' }}>
              AR not supported on this device
            </p>
          )}
        </div>
      )}
      {overlayElements.map(element => (
        <div
          key={element.id}
          style={{
            position: 'absolute',
            left: element.x * 100 + '%',
            top: element.y * 100 + '%',
            transform: 'translate(-50%, -50%)',
            padding: '8px 12px',
            background: 'rgba(6, 182, 212, 0.2)',
            border: `1px solid ${HOLOGRAPHIC_COLORS.primary}`,
            borderRadius: '8px',
            color: HOLOGRAPHIC_COLORS.accent,
            fontSize: '12px',
            backdropFilter: 'blur(8px)'
          }}
        >
          {element.label}
        </div>
      )      )}
    </div>
  )
}

export { VRWorkspace, AROverlay }
