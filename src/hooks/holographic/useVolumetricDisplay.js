import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../../utils/holographic/HolographicConfig'

export function useVolumetricDisplay() {
  const [voxels, setVoxels] = useState([])
  const [isActive, setIsActive] = useState(false)
  const [density, setDensity] = useState(HOLOGRAPHIC_CONFIG.volumetric.density)
  const [emission, setEmission] = useState(HOLOGRAPHIC_CONFIG.volumetric.emission)
  const [absorption, setAbsorption] = useState(HOLOGRAPHIC_CONFIG.volumetric.absorption)
  const [rotation, setRotation] = useState({ x: 0, y: 0, z: 0 })
  const voxelGridRef = useRef([])
  const animationRef = useRef(null)

  const createVoxel = useCallback((x, y, z, color, intensity = 1) => ({
    x, y, z,
    color,
    intensity,
    opacity: 0,
    targetOpacity: intensity * density,
    phase: Math.random() * Math.PI * 2,
    pulseSpeed: 0.5 + Math.random() * 1.5,
    absorption: absorption
  }), [density, absorption])

  const rotatePoint = useCallback((point, rotX, rotY, rotZ) => {
    let { x, y, z } = point

    const cosX = Math.cos(rotX)
    const sinX = Math.sin(rotX)
    const cosY = Math.cos(rotY)
    const sinY = Math.sin(rotY)
    const cosZ = Math.cos(rotZ)
    const sinZ = Math.sin(rotZ)

    let y1 = y * cosX - z * sinX
    let z1 = y * sinX + z * cosX
    y = y1
    z = z1

    let x1 = x * cosY + z * sinY
    z1 = -x * sinY + z * cosY
    x = x1
    z = z1

    x1 = x * cosZ - y * sinZ
    y1 = x * sinZ + y * cosZ
    x = x1
    y = y1

    return { x, y, z }
  }, [])

  const initializeGrid = useCallback((width = 32, height = 32, depth = 32) => {
    const grid = []
    for (let z = 0; z < depth; z++) {
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          grid.push({
            x: (x / width - 0.5) * 2,
            y: (y / height - 0.5) * 2,
            z: (z / depth - 0.5) * 2,
            intensity: 0,
            phase: Math.random() * Math.PI * 2,
            absorption: Math.random() * 0.3
          })
        }
      }
    }
    voxelGridRef.current = grid
    return grid
  }, [])

  const projectVoxelToScreen = useCallback((voxel, viewDistance = 5, fov = 60, rotX = 0, rotY = 0, rotZ = 0) => {
    const rotated = rotatePoint(voxel, rotX, rotY, rotZ)
    const aspect = window.innerWidth / window.innerHeight
    const fovRad = (fov * Math.PI) / 180
    const scale = 1 / Math.tan(fovRad / 2)

    const z = rotated.z + viewDistance
    if (z <= 0.1) return null

    const x = (rotated.x * scale) / (z * aspect) * 0.5 + 0.5
    const y = (rotated.y * scale) / z * 0.5 + 0.5

    const depthFade = Math.max(0, 1 - z / viewDistance)
    const size = Math.max(1, (1 / z) * 60)
    const opacity = Math.max(0, Math.min(1, voxel.intensity * depthFade * density * (1 - voxel.absorption * absorption)))

    return {
      x: x * window.innerWidth,
      y: y * window.innerHeight,
      size,
      opacity,
      z,
      color: voxel.color || '#06b6d4'
    }
  }, [density, absorption, rotatePoint])

  const animateVoxels = useCallback((time) => {
    const grid = voxelGridRef.current
    const projected = []
    const t = time * 0.001
    const rotX = rotation.x + t * 0.2
    const rotY = rotation.y + t * 0.3
    const rotZ = rotation.z + t * 0.1

    grid.forEach((voxel) => {
      const wave = Math.sin(t * voxel.pulseSpeed + voxel.phase) * 0.5 + 0.5
      const distance = Math.sqrt(voxel.x ** 2 + voxel.y ** 2 + voxel.z ** 2)
      const falloff = Math.max(0, 1 - distance / 2.5)

      voxel.intensity = wave * falloff * emission * 0.6

      const projectedVoxel = projectVoxelToScreen(voxel, 5, 60, rotX, rotY, rotZ)
      if (projectedVoxel && projectedVoxel.opacity > 0.02) {
        projected.push(projectedVoxel)
      }
    })

    projected.sort((a, b) => b.z - a.z)
    setVoxels(projected)
    animationRef.current = requestAnimationFrame(animateVoxels)
  }, [projectVoxelToScreen, emission, rotation])

  const startVolumetricDisplay = useCallback((options = {}) => {
    const { width = 32, height = 32, depth = 32 } = options
    initializeGrid(width, height, depth)
    setIsActive(true)
    animationRef.current = requestAnimationFrame(animateVoxels)
  }, [initializeGrid, animateVoxels])

  const stopVolumetricDisplay = useCallback(() => {
    setIsActive(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
    setVoxels([])
  }, [])

  const updateVoxelData = useCallback((data) => {
    const grid = voxelGridRef.current
    if (!grid.length) return

    data.forEach((point, index) => {
      if (index < grid.length) {
        grid[index].intensity = point.intensity || 0
        grid[index].color = point.color || '#06b6d4'
        grid[index].absorption = point.absorption ?? grid[index].absorption
      }
    })
  }, [])

  const loadVolumeData = useCallback(async (volumeData) => {
    const { width, height, depth, data } = volumeData
    const grid = []

    for (let z = 0; z < depth; z++) {
      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          const index = x + y * width + z * width * height
          const value = data[index] || 0
          grid.push({
            x: (x / width - 0.5) * 2,
            y: (y / height - 0.5) * 2,
            z: (z / depth - 0.5) * 2,
            intensity: value,
            phase: Math.random() * Math.PI * 2,
            absorption: Math.random() * 0.3,
            color: getVolumeColor(value)
          })
        }
      }
    }

    voxelGridRef.current = grid
    setVoxels(grid.map(v => ({ ...v, opacity: v.intensity * density })))
  }, [density])

  const getVolumeColor = (value) => {
    const normalized = Math.max(0, Math.min(1, value))
    if (normalized < 0.25) return HOLOGRAPHIC_COLORS.primary
    if (normalized < 0.5) return HOLOGRAPHIC_COLORS.accent
    if (normalized < 0.75) return HOLOGRAPHIC_COLORS.secondary
    return HOLOGRAPHIC_COLORS.quantum
  }

  const updateRotation = useCallback((rx, ry, rz) => {
    setRotation({ x: rx, y: ry, z: rz })
  }, [])

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return {
    voxels,
    isActive,
    density,
    emission,
    absorption,
    rotation,
    startVolumetricDisplay,
    stopVolumetricDisplay,
    updateVoxelData,
    loadVolumeData,
    setDensity,
    setEmission,
    setAbsorption,
    updateRotation,
    initializeGrid
  }
}
