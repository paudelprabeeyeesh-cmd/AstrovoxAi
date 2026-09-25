import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../utils/holographic/HolographicConfig'

export function useDepthAwareInteractions() {
  const [depthMap, setDepthMap] = useState(new Map())
  const [focusedElement, setFocusedElement] = useState(null)
  const [depthLayers, setDepthLayers] = useState([])
  const [isDepthEnabled, setIsDepthEnabled] = useState(true)
  const depthBufferRef = useRef(new Map())
  const raycasterRef = useRef({
    origin: { x: 0, y: 0, z: -5 },
    direction: { x: 0, y: 0, z: 1 }
  })

  const updateDepth = useCallback((elementId, depth, metadata = {}) => {
    const depthValue = Math.max(0, Math.min(1, depth))

    depthBufferRef.current.set(elementId, {
      depth: depthValue,
      timestamp: Date.now(),
      metadata,
      distance: depthValue * HOLOGRAPHIC_CONFIG.depth.far
    })

    setDepthMap(new Map(depthBufferRef.current))
  }, [])

  const getDepth = useCallback((elementId) => {
    return depthBufferRef.current.get(elementId)?.depth || 0.5
  }, [])

  const calculateDepthBlur = useCallback((elementId, focusDepth = 0.5) => {
    const elementDepth = getDepth(elementId)
    const distance = Math.abs(elementDepth - focusDepth)
    const blurAmount = distance * HOLOGRAPHIC_CONFIG.depth.blurTransition * 10

    return Math.min(20, blurAmount)
  }, [getDepth])

  const getDepthScale = useCallback((elementId, focusDepth = 0.5) => {
    const elementDepth = getDepth(elementId)
    const distance = Math.abs(elementDepth - focusDepth)
    const scale = 1 - distance * HOLOGRAPHIC_CONFIG.depth.parallaxFactor * 0.5

    return Math.max(0.5, Math.min(1.2, scale))
  }, [getDepth])

  const getDepthOpacity = useCallback((elementId, focusDepth = 0.5) => {
    const elementDepth = getDepth(elementId)
    const distance = Math.abs(elementDepth - focusDepth)

    const opacity = 1 - distance * HOLOGRAPHIC_CONFIG.depth.parallaxFactor
    return Math.max(0.3, Math.min(1, opacity))
  }, [getDepth])

  const raycast = useCallback((x, y, z = 0) => {
    const origin = raycasterRef.current.origin
    const direction = raycasterRef.current.direction

    const intersections = []

    depthBufferRef.current.forEach((data, elementId) => {
      const elementDepth = data.depth
      const t = (elementDepth - origin.z) / direction.z

      if (t > 0) {
        const hitX = origin.x + direction.x * t
        const hitY = origin.y + direction.y * t

        const distance = Math.sqrt((x - hitX) ** 2 + (y - hitY) ** 2)
        const hitRadius = 0.1 + elementDepth * 0.2

        if (distance < hitRadius) {
          intersections.push({
            elementId,
            distance,
            depth: elementDepth,
            point: { x: hitX, y: hitY, z: elementDepth },
            data
          })
        }
      }
    })

    intersections.sort((a, b) => a.distance - b.distance)

    return intersections.length > 0 ? intersections[0] : null
  }, [])

  const createDepthLayer = useCallback((id, depth, children, options = {}) => {
    const layer = {
      id,
      depth: Math.max(0, Math.min(1, depth)),
      children,
      ...options
    }

    setDepthLayers(prev => {
      const existing = prev.findIndex(l => l.id === id)
      const updated = existing >= 0 ? [...prev] : [...prev, layer]
      if (existing >= 0) updated[existing] = layer
      return updated.sort((a, b) => a.depth - b.depth)
    })

    return layer
  }, [])

  const removeDepthLayer = useCallback((id) => {
    setDepthLayers(prev => prev.filter(l => l.id !== id))
    depthBufferRef.current.delete(id)
  }, [])

  const getDepthSortedElements = useCallback(() => {
    return Array.from(depthBufferRef.current.entries())
      .map(([id, data]) => ({ id, ...data }))
      .sort((a, b) => a.depth - b.depth)
  }, [])

  const calculateParallax = useCallback((depth, mouseX, mouseY) => {
    const centerX = 0.5
    const centerY = 0.5
    const parallaxStrength = HOLOGRAPHIC_CONFIG.depth.parallaxFactor

    const offsetX = (mouseX - centerX) * depth * parallaxStrength * 100
    const offsetY = (mouseY - centerY) * depth * parallaxStrength * 100

    return {
      x: offsetX,
      y: offsetY,
      rotationX: (mouseY - centerY) * depth * parallaxStrength * 10,
      rotationY: (mouseX - centerX) * depth * parallaxStrength * 10
    }
  }, [])

  const focusOnElement = useCallback((elementId) => {
    const data = depthBufferRef.current.get(elementId)
    if (data) {
      setFocusedElement({
        id: elementId,
        depth: data.depth,
        ...data
      })
    }
  }, [])

  const blurElement = useCallback((elementId) => {
    setFocusedElement(prev => {
      if (prev?.id === elementId) {
        return null
      }
      return prev
    })
  }, [])

  useEffect(() => {
    if (!isDepthEnabled) {
      setDepthLayers([])
      depthBufferRef.current.clear()
    }
  }, [isDepthEnabled])

  return {
    depthMap,
    focusedElement,
    depthLayers,
    isDepthEnabled,
    updateDepth,
    getDepth,
    calculateDepthBlur,
    getDepthScale,
    getDepthOpacity,
    raycast,
    createDepthLayer,
    removeDepthLayer,
    getDepthSortedElements,
    calculateParallax,
    focusOnElement,
    blurElement,
    setIsDepthEnabled
  }
}
