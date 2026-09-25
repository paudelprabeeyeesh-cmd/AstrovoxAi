import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG } from '../utils/holographic/HolographicConfig'

export function useEyeTracking() {
  const [isTracking, setIsTracking] = useState(false)
  const [gaze, setGaze] = useState({ x: 0, y: 0, z: 0 })
  const [confidence, setConfidence] = useState(0)
  const [pupilDiameter, setPupilDiameter] = useState({ left: 0, right: 0 })
  const [eyeOpenness, setEyeOpenness] = useState({ left: 1, right: 1 })
  const [gazeHistory, setGazeHistory] = useState([])
  const [foveatedRegion, setFoveatedRegion] = useState({ x: 0.5, y: 0.5, radius: 0.1 })
  const [attentionTarget, setAttentionTarget] = useState(null)
  const animationRef = useRef(null)
  const gazeHistoryRef = useRef([])

  const startTracking = useCallback(async () => {
    if (!navigator.xr) {
      console.warn('WebXR not available for eye tracking')
      return false
    }

    try {
      const session = await navigator.xr.requestSession('immersive-vr', {
        requiredFeatures: ['eye-tracking'],
        optionalFeatures: ['local-floor', 'layers']
      })

      session.addEventListener('end', () => {
        setIsTracking(false)
      })

      setIsTracking(true)
      return true
    } catch (err) {
      console.error('Failed to start eye tracking:', err)
      return false
    }
  }, [])

  const stopTracking = useCallback(() => {
    setIsTracking(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const updateEyeData = useCallback((eyeTrackingData) => {
    const newGaze = {
      x: eyeTrackingData.gaze?.x || 0,
      y: eyeTrackingData.gaze?.y || 0,
      z: eyeTrackingData.gaze?.z || -1
    }

    setGaze(newGaze)

    gazeHistoryRef.current = [...gazeHistoryRef.current.slice(-100), {
      ...newGaze,
      timestamp: Date.now(),
      confidence: eyeTrackingData.confidence || 0.8
    }]

    setGazeHistory([...gazeHistoryRef.current])
    setConfidence(eyeTrackingData.confidence || 0.8)

    if (eyeTrackingData.pupilDiameter) {
      setPupilDiameter({
        left: eyeTrackingData.pupilDiameter.left || 0,
        right: eyeTrackingData.pupilDiameter.right || 0
      })
    }

    if (eyeTrackingData.eyeOpenness) {
      setEyeOpenness({
        left: eyeTrackingData.eyeOpenness.left ?? 1,
        right: eyeTrackingData.eyeOpenness.right ?? 1
      })
    }

    const avgPupil = (pupilDiameter.left + pupilDiameter.right) / 2
    const attentionLevel = avgPupil / 8

    setFoveatedRegion({
      x: (newGaze.x + 1) / 2,
      y: (newGaze.y + 1) / 2,
      radius: 0.05 + (1 - attentionLevel) * 0.1
    })
  }, [pupilDiameter])

  const simulateEyeTracking = useCallback((time) => {
    if (!isTracking) return

    const t = time * 0.001
    const noiseScale = 0.02

    const simulatedGaze = {
      x: Math.sin(t * 0.5) * 0.3 + Math.sin(t * 1.3) * 0.1 + (Math.random() - 0.5) * noiseScale,
      y: Math.cos(t * 0.7) * 0.2 + Math.sin(t * 1.1) * 0.08 + (Math.random() - 0.5) * noiseScale,
      z: -1 + Math.random() * 0.1
    }

    setGaze(simulatedGaze)

    gazeHistoryRef.current = [...gazeHistoryRef.current.slice(-100), {
      ...simulatedGaze,
      timestamp: Date.now(),
      confidence: 0.7 + Math.random() * 0.3
    }]
    setGazeHistory([...gazeHistoryRef.current])

    const simulatedPupil = {
      left: 3 + Math.random() * 3,
      right: 3 + Math.random() * 3
    }
    setPupilDiameter(simulatedPupil)

    const avgPupil = (simulatedPupil.left + simulatedPupil.right) / 2
    setConfidence(0.6 + Math.random() * 0.4)

    const normalizedX = (simulatedGaze.x + 1) / 2
    const normalizedY = (simulatedGaze.y + 1) / 2
    const attentionLevel = avgPupil / 8

    setFoveatedRegion({
      x: normalizedX,
      y: normalizedY,
      radius: 0.05 + (1 - attentionLevel) * 0.1
    })

    animationRef.current = requestAnimationFrame(simulateEyeTracking)
  }, [isTracking])

  const startSimulation = useCallback(() => {
    setIsTracking(true)
    animationRef.current = requestAnimationFrame(simulateEyeTracking)
  }, [simulateEyeTracking])

  const stopSimulation = useCallback(() => {
    setIsTracking(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const getGazePoint = useCallback(() => {
    return {
      x: (gaze.x + 1) / 2,
      y: (gaze.y + 1) / 2
    }
  }, [gaze])

  const getGazeVelocity = useCallback(() => {
    if (gazeHistoryRef.current.length < 2) return { x: 0, y: 0 }

    const recent = gazeHistoryRef.current.slice(-5)
    const first = recent[0]
    const last = recent[recent.length - 1]
    const dt = (last.timestamp - first.timestamp) / 1000

    if (dt <= 0) return { x: 0, y: 0 }

    return {
      x: (last.x - first.x) / dt,
      y: (last.y - first.y) / dt
    }
  }, [])

  const isFixating = useCallback((threshold = 0.02, duration = 200) => {
    const recent = gazeHistoryRef.current.slice(-Math.ceil(duration / 16))
    if (recent.length < 3) return false

    const avgX = recent.reduce((sum, g) => sum + g.x, 0) / recent.length
    const avgY = recent.reduce((sum, g) => sum + g.y, 0) / recent.length

    const variance = recent.reduce((sum, g) => ({
      x: sum.x + (g.x - avgX) ** 2,
      y: sum.y + (g.y - avgY) ** 2
    }), { x: 0, y: 0 })

    const stdX = Math.sqrt(variance.x / recent.length)
    const stdY = Math.sqrt(variance.y / recent.length)

    return stdX < threshold && stdY < threshold
  }, [])

  const getAttentionMap = useCallback((width = 10, height = 10) => {
    const map = Array.from({ length: height }, () => Array(width).fill(0))
    const gazePoint = getGazePoint()

    const centerX = Math.floor(gazePoint.x * width)
    const centerY = Math.floor(gazePoint.y * height)
    const radius = Math.floor(foveatedRegion.radius * Math.max(width, height))

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2)
        const normalizedDist = distance / radius
        map[y][x] = Math.max(0, 1 - normalizedDist)
      }
    }

    return map
  }, [getGazePoint, foveatedRegion.radius])

  const detectBlink = useCallback(() => {
    const avgOpenness = (eyeOpenness.left + eyeOpenness.right) / 2
    return avgOpenness < 0.2
  }, [eyeOpenness])

  const getBlinkRate = useCallback(() => {
    const recent = gazeHistoryRef.current.slice(-5000)
    return recent.length / 5
  }, [])

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return {
    isTracking,
    gaze,
    confidence,
    pupilDiameter,
    eyeOpenness,
    gazeHistory,
    foveatedRegion,
    attentionTarget,
    startTracking,
    stopTracking,
    updateEyeData,
    startSimulation,
    stopSimulation,
    getGazePoint,
    getGazeVelocity,
    isFixating,
    getAttentionMap,
    detectBlink,
    getBlinkRate,
    setAttentionTarget
  }
}
