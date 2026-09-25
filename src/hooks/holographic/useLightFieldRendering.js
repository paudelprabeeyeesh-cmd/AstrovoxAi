import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../utils/holographic/HolographicConfig'

export function useLightFieldRendering() {
  const [lightField, setLightField] = useState(null)
  const [isActive, setIsActive] = useState(false)
  const [resolution, setResolution] = useState(HOLOGRAPHIC_CONFIG.lightField.resolution)
  const canvasRef = useRef(null)
  const animationRef = useRef(null)

  const generateLightField = useCallback((sourceImage, focalPlane = 0.5) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const { width, height } = canvas

    ctx.clearRect(0, 0, width, height)

    const apertureSize = HOLOGRAPHIC_CONFIG.lightField.apertureSize
    const focalLength = HOLOGRAPHIC_CONFIG.lightField.focalLength
    const density = HOLOGRAPHIC_CONFIG.lightField.samplingDensity

    for (let ay = -density; ay <= density; ay++) {
      for (let ax = -density; ax <= density; ax++) {
        const apertureX = (ax / density) * apertureSize
        const apertureY = (ay / density) * apertureSize

        const shiftX = apertureX * focalLength * width
        const shiftY = apertureY * focalLength * height

        const focalShift = focalPlane * width * 0.1

        ctx.globalAlpha = 0.03
        ctx.drawImage(
          sourceImage,
          shiftX + focalShift,
          shiftY + focalShift,
          width,
          height
        )
      }
    }

    ctx.globalAlpha = 1

    const imageData = ctx.getImageData(0, 0, width, height)
    const data = imageData.data

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i]
      const g = data[i + 1]
      const b = data[i + 2]

      const luminance = (r * 0.299 + g * 0.587 + b * 0.114) / 255
      const shift = luminance * 3

      data[i] = Math.min(255, r + shift * 50)
      data[i + 1] = Math.min(255, g + shift * 30)
      data[i + 2] = Math.min(255, b + shift * 70)
    }

    ctx.putImageData(imageData, 0, 0)

    setLightField({
      canvas,
      imageData,
      focalPlane,
      resolution
    })
  }, [resolution])

  const renderLightField = useCallback((time) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const { width, height } = canvas

    ctx.clearRect(0, 0, width, height)

    const centerX = width / 2
    const centerY = height / 2

    for (let y = 0; y < height; y += 2) {
      for (let x = 0; x < width; x += 2) {
        const dx = x - centerX
        const dy = y - centerY
        const distance = Math.sqrt(dx * dx + dy * dy)

        const wave1 = Math.sin(distance * 0.02 - time * 2) * 0.5 + 0.5
        const wave2 = Math.sin(distance * 0.01 + time * 1.5) * 0.5 + 0.5
        const wave3 = Math.sin(x * 0.01 + time) * Math.cos(y * 0.01 + time) * 0.5 + 0.5

        const intensity = (wave1 * 0.5 + wave2 * 0.3 + wave3 * 0.2) * 0.3
        const alpha = intensity * (1 - distance / (Math.max(width, height) * 0.7))

        if (alpha > 0.01) {
          const hue = (distance * 0.2 + time * 20) % 360
          ctx.fillStyle = `hsla(${hue}, 80%, 60%, ${alpha})`
          ctx.fillRect(x, y, 2, 2)
        }
      }
    }

    animationRef.current = requestAnimationFrame(renderLightField)
  }, [])

  const startLightField = useCallback(() => {
    setIsActive(true)
    animationRef.current = requestAnimationFrame(renderLightField)
  }, [renderLightField])

  const stopLightField = useCallback(() => {
    setIsActive(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const captureLightField = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return null

    return canvas.toDataURL('image/png')
  }, [])

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return {
    lightField,
    isActive,
    resolution,
    canvasRef,
    generateLightField,
    renderLightField,
    startLightField,
    stopLightField,
    captureLightField,
    setResolution
  }
}
