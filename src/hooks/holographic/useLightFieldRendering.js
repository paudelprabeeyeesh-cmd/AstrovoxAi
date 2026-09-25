import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../utils/holographic/HolographicConfig'

export function useLightFieldRendering() {
  const [lightField, setLightField] = useState(null)
  const [isActive, setIsActive] = useState(false)
  const [resolution, setResolution] = useState(HOLOGRAPHIC_CONFIG.lightField.resolution)
  const [focalPlane, setFocalPlane] = useState(0.5)
  const [depthMap, setDepthMap] = useState(null)
  const [microLensArray, setMicroLensArray] = useState([])
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

        const focalShift = focalPlane * width * 0.15

        ctx.globalAlpha = 0.04
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
      const shift = luminance * 4

      data[i] = Math.min(255, r + shift * 60)
      data[i + 1] = Math.min(255, g + shift * 40)
      data[i + 2] = Math.min(255, b + shift * 80)
    }

    ctx.putImageData(imageData, 0, 0)

    setLightField({
      canvas,
      imageData,
      focalPlane,
      resolution
    })
  }, [resolution])

  const generateDepthMap = useCallback((sourceImage) => {
    const canvas = canvasRef.current
    if (!canvas || !sourceImage) return

    const ctx = canvas.getContext('2d')
    const { width, height } = canvas

    ctx.clearRect(0, 0, width, height)

    if (sourceImage instanceof HTMLImageElement || sourceImage instanceof HTMLCanvasElement) {
      ctx.drawImage(sourceImage, 0, 0, width, height)
    }

    const imageData = ctx.getImageData(0, 0, width, height)
    const data = imageData.data
    const depthData = new Float32Array(width * height)

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const i = (y * width + x) * 4
        const r = data[i]
        const g = data[i + 1]
        const b = data[i + 2]

        const luminance = (r * 0.299 + g * 0.587 + b * 0.114) / 255
        const gradient = Math.abs(
          (data[((y + 1) * width + x) * 4] - data[((y - 1) * width + x) * 4]) * 0.299 +
          (data[((y + 1) * width + x) * 4 + 1] - data[((y - 1) * width + x) * 4 + 1]) * 0.587 +
          (data[((y + 1) * width + x) * 4 + 2] - data[((y - 1) * width + x) * 4 + 2]) * 0.114
        )

        const depth = (luminance * 0.7 + gradient * 0.3)
        depthData[y * width + x] = Math.min(1, Math.max(0, depth))
      }
    }

    setDepthMap({
      data: depthData,
      width,
      height
    })
  }, [])

  const generateMicroLensArray = useCallback((lensCount = 64) => {
    const lenses = []
    const canvas = canvasRef.current
    if (!canvas) return lenses

    const { width, height } = canvas
    const lensSpacingX = width / Math.sqrt(lensCount)
    const lensSpacingY = height / Math.sqrt(lensCount)
    const lensRadius = Math.min(lensSpacingX, lensSpacingY) * 0.45

    for (let y = lensSpacingY / 2; y < height; y += lensSpacingY) {
      for (let x = lensSpacingX / 2; x < width; x += lensSpacingX) {
        lenses.push({
          x,
          y,
          radius: lensRadius,
          focalLength: 0.05 + Math.random() * 0.02,
          aperture: 0.03
        })
      }
    }

    setMicroLensArray(lenses)
    return lenses
  }, [])

  const refocus = useCallback((newFocalPlane) => {
    setFocalPlane(newFocalPlane)
  }, [])

  const renderLightField = useCallback((time) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const { width, height } = canvas

    ctx.clearRect(0, 0, width, height)

    const centerX = width / 2
    const centerY = height / 2
    const t = time * 0.001

    for (let y = 0; y < height; y += 2) {
      for (let x = 0; x < width; x += 2) {
        const dx = x - centerX
        const dy = y - centerY
        const distance = Math.sqrt(dx * dx + dy * dy)

        const wave1 = Math.sin(distance * 0.025 - t * 2.2) * 0.5 + 0.5
        const wave2 = Math.sin(distance * 0.012 + t * 1.6) * 0.5 + 0.5
        const wave3 = Math.sin(x * 0.012 + t * 1.1) * Math.cos(y * 0.012 + t) * 0.5 + 0.5

        const focalShift = Math.abs(distance / Math.max(width, height) - focalPlane) * 2
        const intensity = (wave1 * 0.5 + wave2 * 0.3 + wave3 * 0.2) * 0.35 * (1 - focalShift)
        const alpha = Math.max(0, intensity * (1 - distance / (Math.max(width, height) * 0.75)))

        if (alpha > 0.01) {
          const hue = (distance * 0.25 + t * 25) % 360
          ctx.fillStyle = `hsla(${hue}, 85%, 65%, ${alpha})`
          ctx.fillRect(x, y, 2, 2)
        }
      }
    }

    if (microLensArray.length > 0) {
      ctx.strokeStyle = `rgba(6, 182, 212, 0.08)`
      ctx.lineWidth = 1
      microLensArray.forEach(lens => {
        ctx.beginPath()
        ctx.arc(lens.x, lens.y, lens.radius, 0, Math.PI * 2)
        ctx.stroke()
      })
    }

    animationRef.current = requestAnimationFrame(renderLightField)
  }, [focalPlane, microLensArray])

  const startLightField = useCallback(() => {
    setIsActive(true)
    generateMicroLensArray()
    animationRef.current = requestAnimationFrame(renderLightField)
  }, [renderLightField, generateMicroLensArray])

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
    focalPlane,
    depthMap,
    microLensArray,
    canvasRef,
    generateLightField,
    generateDepthMap,
    generateMicroLensArray,
    renderLightField,
    startLightField,
    stopLightField,
    captureLightField,
    refocus,
    setResolution,
    setFocalPlane
  }
}
