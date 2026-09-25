import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG } from '../utils/holographic/HolographicConfig'

export function useVolumetricDisplay() {
  const [voxels, setVoxels] = useState([])
  const [isActive, setIsActive] = useState(false)
  const [density, setDensity] = useState(HOLOGRAPHIC_CONFIG.volumetric.density)
  const [emission, setEmission] = useState(HOLOGRAPHIC_CONFIG.volumetric.emission)
  const voxelGridRef = useRef([])
  const animationRef = useRef(null)

  const createVoxel = useCallback((x, y, z, color, intensity = 1) => ({
    x, y, z,
    color,
    intensity,
    opacity: 0,
    targetOpacity: intensity * density,
    phase: Math.random() * Math.PI * 2,
    pulseSpeed: 0.5 + Math.random() * 1.5
  }), [density])

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
            phase: Math.random() * Math.PI * 2
          })
        }
      }
    }
    voxelGridRef.current = grid
    return grid
  }, [])

  const projectVoxelToScreen = useCallback((voxel, viewDistance = 5, fov = 60) => {
    const aspect = window.innerWidth / window.innerHeight
    const fovRad = (fov * Math.PI) / 180
    const scale = 1 / Math.tan(fovRad / 2)

    const z = voxel.z + viewDistance
    if (z <= 0.1) return null

    const x = (voxel.x * scale) / (z * aspect) * 0.5 + 0.5
    const y = (voxel.y * scale) / z * 0.5 + 0.5

    const size = Math.max(1, (1 / z) * 50)

    return {
      x: x * window.innerWidth,
      y: y * window.innerHeight,
      size,
      opacity: Math.max(0, Math.min(1, voxel.intensity * (1 - z / viewDistance) * density)),
      z
    }
  }, [density])

  const animateVoxels = useCallback((time) => {
    const grid = voxelGridRef.current
    const projected = []

    grid.forEach((voxel, index) => {
      const wave = Math.sin(time * voxel.pulseSpeed + voxel.phase) * 0.5 + 0.5
      const distance = Math.sqrt(voxel.x ** 2 + voxel.y ** 2 + voxel.z ** 2)
      const falloff = Math.max(0, 1 - distance / 2)

      voxel.intensity = wave * falloff * emission * 0.5

      const projectedVoxel = projectVoxelToScreen(voxel)
      if (projectedVoxel && projectedVoxel.opacity > 0.01) {
        projected.push({
          ...projectedVoxel,
          color: `rgba(6, 182, 212, ${projectedVoxel.opacity})`
        })
      }
    })

    setVoxels(projected)
    animationRef.current = requestAnimationFrame(animateVoxels)
  }, [projectVoxelToScreen, emission])

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
            phase: Math.random() * Math.PI * 2
          })
        }
      }
    }

    voxelGridRef.current = grid
    setVoxels(grid.map(v => ({ ...v, opacity: v.intensity * density })))
  }, [density])

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
    startVolumetricDisplay,
    stopVolumetricDisplay,
    updateVoxelData,
    loadVolumeData,
    setDensity,
    setEmission,
    initializeGrid
  }
}
