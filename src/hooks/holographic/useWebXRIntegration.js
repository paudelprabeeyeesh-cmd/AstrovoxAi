import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG } from '../../utils/holographic/HolographicConfig'

export function useWebXRIntegration() {
  const [isSupported, setIsSupported] = useState(false)
  const [isInSession, setIsInSession] = useState(false)
  const [session, setSession] = useState(null)
  const [mode, setMode] = useState(HOLOGRAPHIC_CONFIG.xr.defaultMode)
  const [handTracking, setHandTracking] = useState(null)
  const [eyeTracking, setEyeTracking] = useState(null)
  const [spatialAudio, setSpatialAudio] = useState(null)
  const [haptics, setHaptics] = useState(null)
  const [error, setError] = useState(null)
  const xrRef = useRef(null)
  const handJointsRef = useRef({})

  const checkXRSupport = useCallback(async () => {
    if (!navigator.xr) {
      setIsSupported(false)
      return false
    }

    try {
      const supported = await navigator.xr.isSessionSupported('immersive-vr')
      const inlineSupported = await navigator.xr.isSessionSupported('inline')
      const arSupported = await navigator.xr.isSessionSupported('immersive-ar')

      setIsSupported(supported || inlineSupported || arSupported)
      return true
    } catch (err) {
      setError(`XR support check failed: ${err.message}`)
      return false
    }
  }, [])

  const startVRSession = useCallback(async () => {
    if (!navigator.xr) {
      setError('WebXR not available')
      return null
    }

    try {
      const sessionInit = {
        requiredFeatures: HOLOGRAPHIC_CONFIG.xr.requiredFeatures,
        optionalFeatures: HOLOGRAPHIC_CONFIG.xr.optionalFeatures
      }

      const xrSession = await navigator.xr.requestSession('immersive-vr', sessionInit)
      const xrSystem = await navigator.xr.requestSession('immersive-vr', {
        ...sessionInit,
        requiredFeatures: ['local-floor']
      })

      xrRef.current = xrSession
      setSession(xrSession)
      setIsInSession(true)
      setMode('immersive-vr')

      xrSession.addEventListener('end', () => {
        setIsInSession(false)
        setSession(null)
        xrRef.current = null
      })

      if (xrSession.handTracking) {
        setupHandTracking(xrSession)
      }

      if (xrSession.eyeTracking) {
        setupEyeTracking(xrSession)
      }

      setupSpatialAudio(xrSession)
      setupHaptics(xrSession)

      return xrSession
    } catch (err) {
      setError(`Failed to start VR session: ${err.message}`)
      return null
    }
  }, [])

  const startARSession = useCallback(async () => {
    if (!navigator.xr) {
      setError('WebXR not available')
      return null
    }

    try {
      const sessionInit = {
        requiredFeatures: ['hit-test', 'local'],
        optionalFeatures: ['light-estimation', 'image-tracking']
      }

      const xrSession = await navigator.xr.requestSession('immersive-ar', sessionInit)
      xrRef.current = xrSession
      setSession(xrSession)
      setIsInSession(true)
      setMode('immersive-ar')

      xrSession.addEventListener('end', () => {
        setIsInSession(false)
        setSession(null)
        xrRef.current = null
      })

      return xrSession
    } catch (err) {
      setError(`Failed to start AR session: ${err.message}`)
      return null
    }
  }, [])

  const startInlineSession = useCallback(async () => {
    if (!navigator.xr) {
      setError('WebXR not available')
      return null
    }

    try {
      const xrSession = await navigator.xr.requestSession('inline')
      xrRef.current = xrSession
      setSession(xrSession)
      setIsInSession(true)
      setMode('inline')

      xrSession.addEventListener('end', () => {
        setIsInSession(false)
        setSession(null)
        xrRef.current = null
      })

      return xrSession
    } catch (err) {
      setError(`Failed to start inline session: ${err.message}`)
      return null
    }
  }, [])

  const endSession = useCallback(async () => {
    if (xrRef.current) {
      try {
        await xrRef.current.end()
      } catch (err) {
        console.error('Error ending XR session:', err)
      }
      xrRef.current = null
      setSession(null)
      setIsInSession(false)
    }
  }, [])

  const setupHandTracking = useCallback((xrSession) => {
    if (!xrSession.handTracking) return

    const hand0 = xrSession.inputSources.find(s => s.hand)
    if (hand0) {
      setHandTracking({
        left: hand0,
        joints: hand0.joints
      })

      hand0.joints.forEach((joint, index) => {
        handJointsRef.current[index] = {
          position: joint.position,
          radius: joint.radius,
          tracked: joint.tracked
        }
      })
    }
  }, [])

  const setupEyeTracking = useCallback((xrSession) => {
    if (!xrSession.eyeTracking) return

    setEyeTracking({
      gaze: { x: 0, y: 0, z: 0 },
      confidence: 0,
      pupilDiameter: { left: 0, right: 0 },
      eyeOpenness: { left: 1, right: 1 }
    })
  }, [])

  const setupSpatialAudio = useCallback((xrSession) => {
    if (!xrSession.audio) return

    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const panner = audioContext.createPanner()
    panner.panningModel = 'HRTF'
    panner.distanceModel = 'inverse'
    panner.refDistance = 1
    panner.maxDistance = 10000
    panner.rolloffFactor = 1
    panner.coneInnerAngle = 360
    panner.coneOuterAngle = 360
    panner.coneOuterGain = 0

    setSpatialAudio({
      context: audioContext,
      panner,
      listener: audioContext.listener,
      sources: new Map()
    })
  }, [])

  const setupHaptics = useCallback((xrSession) => {
    setHaptics({
      supported: 'vibrate' in navigator,
      actuators: [],
      patterns: {
        light: [10],
        medium: [50],
        heavy: [100],
        pulse: [10, 50, 10],
        wave: [10, 20, 30, 20, 10]
      }
    })
  }, [])

  const updateHandTracking = useCallback((frame) => {
    if (!session || !session.handTracking) return

    for (const source of session.inputSources) {
      if (source.hand && source.hand.values) {
        const joints = source.hand.values()
        const positions = []

        joints.forEach((joint, index) => {
          const pose = frame.getJointPose(joint, session.referenceSpace)
          if (pose) {
            positions.push({
              index,
              position: pose.transform.position,
              orientation: pose.transform.orientation,
              radius: joint.radius || 0.01
            })
          }
        })

        setHandTracking({
          source,
          joints: positions,
          handedness: source.handedness
        })
      }
    }
  }, [session])

  const updateEyeTracking = useCallback((eyeTrackingData) => {
    setEyeTracking(prev => ({
      ...prev,
      ...eyeTrackingData,
      confidence: eyeTrackingData.confidence || 0.8,
      timestamp: Date.now()
    }))
  }, [])

  const vibrate = useCallback((pattern = 'medium', intensity = 1) => {
    if (!haptics?.supported) return

    const hapticPattern = haptics.patterns[pattern] || haptics.patterns.medium
    const duration = hapticPattern[0] * intensity

    if (navigator.vibrate) {
      navigator.vibrate(duration)
    }

    if (session?.inputSources) {
      for (const source of session.inputSources) {
        if (source.gamepad?.hapticActuators) {
          source.gamepad.hapticActuators[0].pulse(intensity, duration)
        }
      }
    }
  }, [haptics, session])

  const playSpatialSound = useCallback((audioBuffer, position, options = {}) => {
    if (!spatialAudio) return null

    const { context, panner } = spatialAudio
    const source = context.createBufferSource()
    source.buffer = audioBuffer
    source.connect(panner)

    if (position) {
      panner.positionX.value = position.x || 0
      panner.positionY.value = position.y || 0
      panner.positionZ.value = position.z || 0
    }

    const gainNode = context.createGain()
    gainNode.gain.value = options.volume || 1
    panner.connect(gainNode)
    gainNode.connect(context.destination)

    source.start(options.startTime || 0)
    source.stop(options.duration ? options.startTime + options.duration : 0)

    return { source, panner, gainNode }
  }, [spatialAudio])

  useEffect(() => {
    checkXRSupport()

    return () => {
      endSession()
    }
  }, [checkXRSupport, endSession])

  return {
    isSupported,
    isInSession,
    session,
    mode,
    handTracking,
    eyeTracking,
    spatialAudio,
    haptics,
    error,
    startVRSession,
    startARSession,
    startInlineSession,
    endSession,
    setupHandTracking,
    setupEyeTracking,
    updateHandTracking,
    updateEyeTracking,
    vibrate,
    playSpatialSound,
    checkXRSupport
  }
}
