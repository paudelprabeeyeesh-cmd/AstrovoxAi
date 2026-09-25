import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG } from '../../utils/holographic/HolographicConfig'

export function useSpatialAudio() {
  const [isActive, setIsActive] = useState(false)
  const [context, setContext] = useState(null)
  const [listener, setListener] = useState(null)
  const [sources, setSources] = useState(new Map())
  const [audioEnabled, setAudioEnabled] = useState(true)
  const audioContextRef = useRef(null)
  const masterGainRef = useRef(null)
  const pannerRef = useRef(null)

  const initializeAudio = useCallback(async () => {
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      const audioCtx = new AudioContextClass()

      const masterGain = audioCtx.createGain()
      masterGain.gain.value = 1.0
      masterGain.connect(audioCtx.destination)

      const panner = audioCtx.createPanner()
      panner.panningModel = 'HRTF'
      panner.distanceModel = 'inverse'
      panner.refDistance = 1
      panner.maxDistance = 10000
      panner.rolloffFactor = 1
      panner.coneInnerAngle = 360
      panner.coneOuterAngle = 360
      panner.coneOuterGain = 0
      panner.connect(masterGain)

      audioContextRef.current = audioCtx
      masterGainRef.current = masterGain
      pannerRef.current = panner

      setContext(audioCtx)
      setListener(audioCtx.listener)
      setIsActive(true)

      return audioCtx
    } catch (err) {
      console.error('Failed to initialize spatial audio:', err)
      return null
    }
  }, [])

  const createSpatialSource = useCallback((options = {}) => {
    const audioCtx = audioContextRef.current
    if (!audioCtx) return null

    const {
      position = { x: 0, y: 0, z: -2 },
      velocity = { x: 0, y: 0, z: 0 },
      direction = { x: 0, y: 0, z: -1 },
      volume = 1.0,
      loop = false,
      buffer = null
    } = options

    const source = audioCtx.createBufferSource()
    source.loop = loop
    source.buffer = buffer

    const sourcePanner = audioCtx.createPanner()
    sourcePanner.panningModel = 'HRTF'
    sourcePanner.distanceModel = 'inverse'
    sourcePanner.refDistance = 1
    sourcePanner.maxDistance = 10000
    sourcePanner.rolloffFactor = 1
    sourcePanner.coneInnerAngle = 360
    sourcePanner.coneOuterAngle = 360
    sourcePanner.coneOuterGain = 0

    sourcePanner.positionX.value = position.x
    sourcePanner.positionY.value = position.y
    sourcePanner.positionZ.value = position.z

    const gainNode = audioCtx.createGain()
    gainNode.gain.value = volume

    source.connect(sourcePanner)
    sourcePanner.connect(gainNode)
    gainNode.connect(masterGainRef.current || audioCtx.destination)

    const sourceId = Date.now() + Math.random().toString(36).substr(2, 9)
    const sourceData = {
      id: sourceId,
      source,
      panner: sourcePanner,
      gain: gainNode,
      position,
      velocity,
      direction,
      volume,
      loop,
      isPlaying: false
    }

    setSources(prev => new Map(prev).set(sourceId, sourceData))
    return sourceData
  }, [])

  const playSpatialSound = useCallback((sourceId, startTime = 0, duration = null) => {
    const audioCtx = audioContextRef.current
    const sourceData = sources.get(sourceId)
    if (!audioCtx || !sourceData) return false

    try {
      sourceData.source.start(startTime)
      if (duration) {
        sourceData.source.stop(startTime + duration)
      }

      setSources(prev => {
        const updated = new Map(prev)
        const current = updated.get(sourceId)
        if (current) {
          updated.set(sourceId, { ...current, isPlaying: true })
        }
        return updated
      })

      return true
    } catch (err) {
      console.error('Failed to play spatial sound:', err)
      return false
    }
  }, [sources])

  const stopSpatialSound = useCallback((sourceId) => {
    const sourceData = sources.get(sourceId)
    if (!sourceData) return

    try {
      sourceData.source.stop()
      setSources(prev => {
        const updated = new Map(prev)
        const current = updated.get(sourceId)
        if (current) {
          updated.set(sourceId, { ...current, isPlaying: false })
        }
        return updated
      })
    } catch (err) {
      console.error('Failed to stop spatial sound:', err)
    }
  }, [sources])

  const updateSourcePosition = useCallback((sourceId, position) => {
    setSources(prev => {
      const updated = new Map(prev)
      const current = updated.get(sourceId)
      if (current && current.panner) {
        current.panner.positionX.value = position.x
        current.panner.positionY.value = position.y
        current.panner.positionZ.value = position.z
        updated.set(sourceId, { ...current, position })
      }
      return updated
    })
  }, [])

  const updateListenerPosition = useCallback((position, orientation = { x: 0, y: 0, z: -1, w: 1 }) => {
    const audioCtx = audioContextRef.current
    if (!audioCtx || !audioCtx.listener) return

    const listener = audioCtx.listener
    if (listener.positionX) {
      listener.positionX.value = position.x
      listener.positionY.value = position.y
      listener.positionZ.value = position.z
    } else if (listener.setPosition) {
      listener.setPosition(position.x, position.y, position.z)
    }

    if (listener.forwardX) {
      listener.forwardX.value = orientation.x
      listener.forwardY.value = orientation.y
      listener.forwardZ.value = orientation.z
      listener.upX.value = 0
      listener.upY.value = 1
      listener.upZ.value = 0
    } else if (listener.setOrientation) {
      listener.setOrientation(orientation.x, orientation.y, orientation.z, orientation.w)
    }
  }, [])

  const removeSource = useCallback((sourceId) => {
    const sourceData = sources.get(sourceId)
    if (sourceData) {
      try {
        if (sourceData.isPlaying) {
          sourceData.source.stop()
        }
      } catch (err) {
        console.error('Failed to remove source:', err)
      }
    }

    setSources(prev => {
      const updated = new Map(prev)
      updated.delete(sourceId)
      return updated
    })
  }, [sources])

  const setMasterVolume = useCallback((volume) => {
    if (masterGainRef.current) {
      masterGainRef.current.gain.value = Math.max(0, Math.min(1, volume))
    }
  }, [])

  const enableOcclusion = useCallback((enable) => {
    if (pannerRef.current) {
      pannerRef.current.refDistance = enable ? 1 : 0.1
    }
  }, [])

  const suspend = useCallback(() => {
    audioContextRef.current?.suspend()
    setIsActive(false)
  }, [])

  const resume = useCallback(() => {
    audioContextRef.current?.resume()
    setIsActive(true)
  }, [])

  const destroy = useCallback(() => {
    sources.forEach((sourceData, sourceId) => {
      try {
        if (sourceData.isPlaying) {
          sourceData.source.stop()
        }
      } catch (err) {
        console.error('Failed to destroy source:', err)
      }
    })

    audioContextRef.current?.close()
    audioContextRef.current = null
    masterGainRef.current = null
    pannerRef.current = null
    setSources(new Map())
    setContext(null)
    setListener(null)
    setIsActive(false)
  }, [sources])

  useEffect(() => {
    return () => {
      destroy()
    }
  }, [destroy])

  return {
    isActive,
    context,
    listener,
    sources,
    audioEnabled,
    initializeAudio,
    createSpatialSource,
    playSpatialSound,
    stopSpatialSound,
    updateSourcePosition,
    updateListenerPosition,
    removeSource,
    setMasterVolume,
    enableOcclusion,
    suspend,
    resume,
    destroy,
    setAudioEnabled
  }
}
