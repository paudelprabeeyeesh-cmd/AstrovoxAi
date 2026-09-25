import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG } from '../utils/holographic/HolographicConfig'

export function useHapticFeedback() {
  const [isSupported, setIsSupported] = useState(false)
  const [isEnabled, setIsEnabled] = useState(true)
  const [actuators, setActuators] = useState([])
  const [intensity, setIntensity] = useState(1.0)
  const [pattern, setPattern] = useState('medium')
  const [hapticHistory, setHapticHistory] = useState([])
  const historyRef = useRef([])

  const PATTERNS = {
    light: { duration: 10, intensity: 0.3 },
    medium: { duration: 50, intensity: 0.6 },
    heavy: { duration: 100, intensity: 1.0 },
    pulse: { duration: 30, intensity: 0.8 },
    wave: { duration: 60, intensity: 0.5 },
    double: { duration: 20, intensity: 0.7 },
    triple: { duration: 15, intensity: 0.6 },
    continuous: { duration: 200, intensity: 0.4 },
    sharp: { duration: 5, intensity: 1.0 },
    soft: { duration: 80, intensity: 0.3 }
  }

  const checkSupport = useCallback(async () => {
    const supported = 'vibrate' in navigator || 'hapticActuators' in window
    setIsSupported(supported)
    return supported
  }, [])

  const initializeActuators = useCallback(async (xrSession) => {
    const newActuators = []

    if (xrSession?.inputSources) {
      for (const source of xrSession.inputSources) {
        if (source.gamepad?.hapticActuators) {
          for (const actuator of source.gamepad.hapticActuators) {
            newActuators.push({
              type: actuator.type || 'vibration',
              source: source.handedness,
              actuator
            })
          }
        }
      }
    }

    setActuators(newActuators)
    return newActuators
  }, [])

  const vibrate = useCallback((patternType = 'medium', customIntensity = null) => {
    if (!isSupported || !isEnabled) return false

    const patternConfig = PATTERNS[patternType] || PATTERNS.medium
    const finalIntensity = customIntensity ?? intensity
    const duration = patternConfig.duration * finalIntensity

    const hapticEvent = {
      id: Date.now(),
      pattern: patternType,
      intensity: finalIntensity,
      duration,
      timestamp: Date.now()
    }

    historyRef.current = [...historyRef.current.slice(-100), hapticEvent]
    setHapticHistory([...historyRef.current])

    if (navigator.vibrate && patternType === 'medium') {
      navigator.vibrate(duration)
    }

    actuators.forEach(actuator => {
      try {
        if (actuator.actuator?.pulse) {
          actuator.actuator.pulse(finalIntensity, duration)
        }
      } catch (err) {
        console.error('Haptic pulse failed:', err)
      }
    })

    return true
  }, [isSupported, isEnabled, intensity, actuators])

  const playPattern = useCallback((patternName, options = {}) => {
    if (!isSupported || !isEnabled) return false

    const patternConfig = PATTERNS[patternName] || PATTERNS.medium
    const {
      intensity: customIntensity = intensity,
      repeat = false,
      customDuration = null
    } = options

    const duration = customDuration ?? patternConfig.duration
    const finalIntensity = customIntensity * patternConfig.intensity

    const playPatternStep = (step = 0) => {
      if (!isEnabled) return

      vibrate(patternName, customIntensity)

      if (repeat && step < 10) {
        setTimeout(() => playPatternStep(step + 1), duration + 50)
      }
    }

    playPatternStep()
    return true
  }, [isSupported, isEnabled, intensity, vibrate])

  const pulseAtPosition = useCallback((x, y, z, intensity = 1.0) => {
    if (!isSupported || !isEnabled) return false

    const distance = Math.sqrt(x * x + y * y + z * z)
    const attenuation = Math.max(0, 1 - distance / 10)
    const finalIntensity = intensity * attenuation

    if (finalIntensity > 0.1) {
      vibrate('medium', finalIntensity)
    }

    return true
  }, [isSupported, isEnabled, vibrate])

  const triggerOnEvent = useCallback((eventType, options = {}) => {
    const eventPatterns = {
      select: 'light',
      activate: 'medium',
      hover: 'soft',
      grab: 'heavy',
      release: 'light',
      collision: 'sharp',
      success: 'double',
      error: 'triple',
      notification: 'pulse'
    }

    const pattern = eventPatterns[eventType] || 'medium'
    return vibrate(pattern, options.intensity)
  }, [vibrate])

  const clearHistory = useCallback(() => {
    historyRef.current = []
    setHapticHistory([])
  }, [])

  const getLastHaptic = useCallback(() => {
    return historyRef.current[historyRef.current.length - 1] || null
  }, [])

  const getHapticFrequency = useCallback((windowMs = 5000) => {
    const now = Date.now()
    const recent = historyRef.current.filter(h => now - h.timestamp < windowMs)
    return recent.length / (windowMs / 1000)
  }, [])

  useEffect(() => {
    checkSupport()

    return () => {
      if (navigator.vibrate) {
        navigator.vibrate(0)
      }
    }
  }, [checkSupport])

  return {
    isSupported,
    isEnabled,
    actuators,
    intensity,
    pattern,
    hapticHistory,
    PATTERNS,
    checkSupport,
    initializeActuators,
    vibrate,
    playPattern,
    pulseAtPosition,
    triggerOnEvent,
    clearHistory,
    getLastHaptic,
    getHapticFrequency,
    setIsEnabled,
    setIntensity,
    setPattern
  }
}
