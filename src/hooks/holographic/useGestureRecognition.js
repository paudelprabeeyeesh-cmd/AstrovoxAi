import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG } from '../utils/holographic/HolographicConfig'

export function useGestureRecognition() {
  const [gesture, setGesture] = useState(null)
  const [confidence, setConfidence] = useState(0)
  const [isTracking, setIsTracking] = useState(false)
  const [gestureHistory, setGestureHistory] = useState([])
  const [recognizedGestures, setRecognizedGestures] = useState([])

  const trackRef = useRef(null)
  const pointsRef = useRef([])
  const gestureStartRef = useRef(null)
  const gestureLibraryRef = useRef(HOLOGRAPHIC_CONFIG.gesture.gestureLibrary)

  const startTracking = useCallback(() => {
    setIsTracking(true)
    pointsRef.current = []
    gestureStartRef.current = Date.now()
    trackRef.current = requestAnimationFrame(trackLoop)
  }, [])

  const stopTracking = useCallback(() => {
    setIsTracking(false)
    if (trackRef.current) {
      cancelAnimationFrame(trackRef.current)
      trackRef.current = null
    }
  }, [])

  const trackLoop = useCallback(() => {
    if (!isTracking) return

    const now = Date.now()
    const timeSinceStart = now - (gestureStartRef.current || now)

    if (timeSinceStart > HOLOGRAPHIC_CONFIG.gesture.recognitionWindow) {
      recognizeGesture()
      gestureStartRef.current = now
      pointsRef.current = []
    }

    trackRef.current = requestAnimationFrame(trackLoop)
  }, [isTracking])

  const addPoint = useCallback((x, y, z = 0) => {
    if (!isTracking) return

    const point = {
      x,
      y,
      z,
      timestamp: Date.now(),
      velocity: { x: 0, y: 0, z: 0 }
    }

    if (pointsRef.current.length > 0) {
      const lastPoint = pointsRef.current[pointsRef.current.length - 1]
      const dt = (point.timestamp - lastPoint.timestamp) / 1000
      if (dt > 0) {
        point.velocity = {
          x: (point.x - lastPoint.x) / dt,
          y: (point.y - lastPoint.y) / dt,
          z: (point.z - lastPoint.z) / dt
        }
      }
    }

    pointsRef.current.push(point)

    if (pointsRef.current.length > 100) {
      pointsRef.current = pointsRef.current.slice(-100)
    }
  }, [isTracking])

  const recognizeGesture = useCallback(() => {
    const points = pointsRef.current
    if (points.length < 10) {
      setGesture(null)
      setConfidence(0)
      return
    }

    const gestures = {
      swipe: detectSwipe(points),
      pinch: detectPinch(points),
      rotate: detectRotate(points),
      wave: detectWave(points),
      point: detectPoint(points),
      grab: detectGrab(points),
      release: detectRelease(points),
      push: detectPush(points)
    }

    let bestGesture = null
    let bestConfidence = 0

    Object.entries(gestures).forEach(([name, result]) => {
      if (result.confidence > bestConfidence && result.confidence > HOLOGRAPHIC_CONFIG.gesture.confidence) {
        bestGesture = name
        bestConfidence = result.confidence
      }
    })

    if (bestGesture) {
      setGesture(bestGesture)
      setConfidence(bestConfidence)
      setGestureHistory(prev => [...prev.slice(-50), {
        gesture: bestGesture,
        confidence: bestConfidence,
        timestamp: Date.now()
      }])
      setRecognizedGestures(prev => [...prev.slice(-100), bestGesture])
    }
  }, [])

  const detectSwipe = (points) => {
    if (points.length < 10) return { gesture: 'swipe', confidence: 0 }

    const start = points[0]
    const end = points[points.length - 1]
    const dx = end.x - start.x
    const dy = end.y - start.y
    const distance = Math.sqrt(dx * dx + dy * dy)

    if (distance < 0.1) return { gesture: 'swipe', confidence: 0 }

    const avgVelocity = points.reduce((sum, p) => sum + Math.sqrt(p.velocity.x ** 2 + p.velocity.y ** 2), 0) / points.length

    const direction = dx > dy ? 'horizontal' : 'vertical'
    const directionConfidence = Math.abs(dx / distance)

    return {
      gesture: 'swipe',
      confidence: Math.min(1, (distance * 0.5 + avgVelocity * 0.1) * directionConfidence)
    }
  }

  const detectPinch = (points) => {
    if (points.length < 15) return { gesture: 'pinch', confidence: 0 }

    const recent = points.slice(-15)
    const distances = []

    for (let i = 1; i < recent.length; i++) {
      const dx = recent[i].x - recent[i - 1].x
      const dy = recent[i].y - recent[i - 1].y
      distances.push(Math.sqrt(dx * dx + dy * dy))
    }

    const avgDistance = distances.reduce((a, b) => a + b, 0) / distances.length
    const minDistance = Math.min(...distances)
    const maxDistance = Math.max(...distances)

    const convergence = maxDistance > 0 ? (maxDistance - minDistance) / maxDistance : 0

    return {
      gesture: 'pinch',
      confidence: convergence > 0.3 ? Math.min(1, convergence) : 0
    }
  }

  const detectRotate = (points) => {
    if (points.length < 20) return { gesture: 'rotate', confidence: 0 }

    const center = {
      x: points.reduce((sum, p) => sum + p.x, 0) / points.length,
      y: points.reduce((sum, p) => sum + p.y, 0) / points.length
    }

    const angles = points.map(p => Math.atan2(p.y - center.y, p.x - center.x))

    let totalRotation = 0
    for (let i = 1; i < angles.length; i++) {
      let diff = angles[i] - angles[i - 1]
      if (diff > Math.PI) diff -= 2 * Math.PI
      if (diff < -Math.PI) diff += 2 * Math.PI
      totalRotation += diff
    }

    const avgDistance = points.reduce((sum, p) => {
      const dx = p.x - center.x
      const dy = p.y - center.y
      return sum + Math.sqrt(dx * dx + dy * dy)
    }, 0) / points.length

    return {
      gesture: 'rotate',
      confidence: avgDistance > 0.05 ? Math.min(1, Math.abs(totalRotation) * 0.5) : 0
    }
  }

  const detectWave = (points) => {
    if (points.length < 30) return { gesture: 'wave', confidence: 0 }

    const yValues = points.map(p => p.y)
    const yRange = Math.max(...yValues) - Math.min(...yValues)
    const xValues = points.map(p => p.x)
    const xRange = Math.max(...xValues) - Math.min(...xValues)

    const oscillations = countOscillations(yValues)

    return {
      gesture: 'wave',
      confidence: yRange > 0.1 && oscillations > 3 ? Math.min(1, oscillations * 0.2) : 0
    }
  }

  const detectPoint = (points) => {
    if (points.length < 5) return { gesture: 'point', confidence: 0 }

    const recent = points.slice(-10)
    const avgVelocity = recent.reduce((sum, p) => sum + Math.sqrt(p.velocity.x ** 2 + p.velocity.y ** 2), 0) / recent.length
    const position = recent[recent.length - 1]

    const velocityLow = avgVelocity < 0.5

    return {
      gesture: 'point',
      confidence: velocityLow ? 0.8 : 0
    }
  }

  const detectGrab = (points) => {
    if (points.length < 20) return { gesture: 'grab', confidence: 0 }

    const recent = points.slice(-20)
    const distances = []

    for (let i = 1; i < recent.length; i++) {
      const dx = recent[i].x - recent[i - 1].x
      const dy = recent[i].y - recent[i - 1].y
      distances.push(Math.sqrt(dx * dx + dy * dy))
    }

    const avgDistance = distances.reduce((a, b) => a + b, 0) / distances.length
    const convergence = distances[0] > 0 ? (distances[0] - avgDistance) / distances[0] : 0

    return {
      gesture: 'grab',
      confidence: convergence > 0.3 ? Math.min(1, convergence) : 0
    }
  }

  const detectRelease = (points) => {
    if (points.length < 15) return { gesture: 'release', confidence: 0 }

    const recent = points.slice(-15)
    const distances = []

    for (let i = 1; i < recent.length; i++) {
      const dx = recent[i].x - recent[i - 1].x
      const dy = recent[i].y - recent[i - 1].y
      distances.push(Math.sqrt(dx * dx + dy * dy))
    }

    const avgDistance = distances.reduce((a, b) => a + b, 0) / distances.length
    const divergence = distances[distances.length - 1] > 0 ? (distances[distances.length - 1] - avgDistance) / distances[distances.length - 1] : 0

    return {
      gesture: 'release',
      confidence: divergence > 0.3 ? Math.min(1, divergence) : 0
    }
  }

  const detectPush = (points) => {
    if (points.length < 10) return { gesture: 'push', confidence: 0 }

    const recent = points.slice(-10)
    const zValues = recent.map(p => p.z || 0)
    const avgZ = zValues.reduce((a, b) => a + b, 0) / zValues.length
    const zVelocity = zValues.length > 1 ? (zValues[zValues.length - 1] - zValues[0]) / zValues.length : 0

    return {
      gesture: 'push',
      confidence: avgZ > 0.3 && zVelocity < -0.1 ? Math.min(1, Math.abs(zVelocity) * 5) : 0
    }
  }

  const countOscillations = (values) => {
    let count = 0
    let prevSlope = 0

    for (let i = 1; i < values.length; i++) {
      const slope = values[i] - values[i - 1]
      if ((slope > 0 && prevSlope < 0) || (slope < 0 && prevSlope > 0)) {
        count++
      }
      prevSlope = slope
    }

    return count
  }

  const clearHistory = useCallback(() => {
    setGestureHistory([])
    setRecognizedGestures([])
  }, [])

  useEffect(() => {
    return () => {
      if (trackRef.current) {
        cancelAnimationFrame(trackRef.current)
      }
    }
  }, [])

  return {
    gesture,
    confidence,
    isTracking,
    gestureHistory,
    recognizedGestures,
    startTracking,
    stopTracking,
    addPoint,
    clearHistory,
    recognizeGesture
  }
}
