import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG } from '../../utils/holographic/HolographicConfig'

export function useHandTracking() {
  const [isTracking, setIsTracking] = useState(false)
  const [hands, setHands] = useState({ left: null, right: null })
  const [joints, setJoints] = useState([])
  const [gestures, setGestures] = useState([])
  const [confidence, setConfidence] = useState(0)
  const [pinchDistance, setPinchDistance] = useState(0)
  const [grabStrength, setGrabStrength] = useState(0)
  const [pointing, setPointing] = useState(false)
  const animationRef = useRef(null)
  const jointsRef = useRef([])
  const gestureHistoryRef = useRef([])

  const JOINT_NAMES = [
    'wrist',
    'thumb-metacarpal', 'thumb-phalanx-proximal', 'thumb-phalanx-distal', 'thumb-tip',
    'index-finger-metacarpal', 'index-finger-phalanx-proximal', 'index-finger-phalanx-intermediate', 'index-finger-phalanx-distal', 'index-finger-tip',
    'middle-finger-metacarpal', 'middle-finger-phalanx-proximal', 'middle-finger-phalanx-intermediate', 'middle-finger-phalanx-distal', 'middle-finger-tip',
    'ring-finger-metacarpal', 'ring-finger-phalanx-proximal', 'ring-finger-phalanx-intermediate', 'ring-finger-phalanx-distal', 'ring-finger-tip',
    'pinky-finger-metacarpal', 'pinky-finger-phalanx-proximal', 'pinky-finger-phalanx-intermediate', 'pinky-finger-phalanx-distal', 'pinky-finger-tip'
  ]

  const startTracking = useCallback(async () => {
    if (!navigator.xr) {
      console.warn('WebXR not available for hand tracking')
      return false
    }

    try {
      const session = await navigator.xr.requestSession('immersive-vr', {
        requiredFeatures: ['hand-tracking'],
        optionalFeatures: ['local-floor']
      })

      session.addEventListener('end', () => {
        setIsTracking(false)
        setHands({ left: null, right: null })
      })

      const hand0 = session.inputSources.find(s => s.hand)
      if (hand0) {
        setHands(prev => ({ ...prev, right: hand0 }))
        extractJoints(hand0)
      }

      setIsTracking(true)
      return true
    } catch (err) {
      console.error('Failed to start hand tracking:', err)
      return false
    }
  }, [])

  const stopTracking = useCallback(() => {
    setIsTracking(false)
    setHands({ left: null, right: null })
    setJoints([])
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const extractJoints = useCallback((hand) => {
    if (!hand || !hand.joints) return []

    const extractedJoints = []
    hand.joints.forEach((joint, index) => {
      extractedJoints.push({
        index,
        name: JOINT_NAMES[index] || `joint-${index}`,
        position: joint.position ? { x: joint.position.x, y: joint.position.y, z: joint.position.z } : { x: 0, y: 0, z: 0 },
        orientation: joint.orientation || { x: 0, y: 0, z: 0, w: 1 },
        radius: joint.radius || 0.01,
        tracked: joint.tracked || false
      })
    })

    jointsRef.current = extractedJoints
    setJoints(extractedJoints)
    return extractedJoints
  }, [])

  const updateHandData = useCallback((frame, session) => {
    if (!session) return

    for (const source of session.inputSources) {
      if (source.hand && source.hand.values) {
        const handedness = source.handedness
        const joints = source.hand.values()

        const jointData = Array.from(joints).map((joint, index) => {
          const pose = frame.getJointPose(joint, session.referenceSpace)
          return {
            index,
            name: JOINT_NAMES[index] || `joint-${index}`,
            position: pose?.transform?.position || { x: 0, y: 0, z: 0 },
            orientation: pose?.transform?.orientation || { x: 0, y: 0, z: 0, w: 1 },
            radius: joint.radius || 0.01,
            tracked: pose?.tracked || false
          }
        })

        jointsRef.current = jointData
        setJoints(jointData)
        setHands(prev => ({
          ...prev,
          [handedness]: { source, joints: jointData }
        }))

        detectHandGestures(jointData)
      }
    }
  }, [])

  const detectHandGestures = useCallback((handJoints) => {
    if (!handJoints || handJoints.length < 25) return

    const wrist = handJoints[0]
    const thumbTip = handJoints[4]
    const indexTip = handJoints[8]
    const middleTip = handJoints[12]
    const ringTip = handJoints[16]
    const pinkyTip = handJoints[20]

    const thumbIndexDist = Math.sqrt(
      (thumbTip.position.x - indexTip.position.x) ** 2 +
      (thumbTip.position.y - indexTip.position.y) ** 2 +
      (thumbTip.position.z - indexTip.position.z) ** 2
    )

    const indexMiddleDist = Math.sqrt(
      (indexTip.position.x - middleTip.position.x) ** 2 +
      (indexTip.position.y - middleTip.position.y) ** 2 +
      (indexTip.position.z - middleTip.position.z) ** 2
    )

    setPinchDistance(thumbIndexDist)

    const isPinching = thumbIndexDist < 0.03
    const isPointing = indexMiddleDist > 0.05 && thumbIndexDist > 0.05

    setPointing(isPointing && !isPinching)

    const fingerTips = [indexTip, middleTip, ringTip, pinkyTip]
    const avgFingerY = fingerTips.reduce((sum, tip) => sum + tip.position.y, 0) / fingerTips.length
    const wristY = wrist.position.y
    const fingersExtended = avgFingerY > wristY + 0.02

    setGrabStrength(fingersExtended ? 0.2 : 0.8)

    const newGestures = []
    if (isPinching) newGestures.push('pinch')
    if (isPointing) newGestures.push('point')
    if (fingersExtended && !isPinching) newGestures.push('open_palm')
    if (!fingersExtended && !isPinching) newGestures.push('fist')

    if (newGestures.length > 0) {
      setGestures(newGestures)
      gestureHistoryRef.current = [...gestureHistoryRef.current.slice(-50), {
        gestures: newGestures,
        timestamp: Date.now(),
        pinchDistance: thumbIndexDist
      }]
    }
  }, [])

  const simulateHandTracking = useCallback((time) => {
    if (!isTracking) return

    const t = time * 0.001
    const simulatedJoints = JOINT_NAMES.map((name, index) => {
      const baseX = Math.sin(t * 2 + index * 0.5) * 0.3
      const baseY = Math.cos(t * 1.5 + index * 0.3) * 0.2 + 1.2
      const baseZ = Math.sin(t * 1.8 + index * 0.4) * 0.2 - 0.5

      return {
        index,
        name,
        position: {
          x: baseX + (Math.random() - 0.5) * 0.02,
          y: baseY + (Math.random() - 0.5) * 0.02,
          z: baseZ + (Math.random() - 0.5) * 0.02
        },
        orientation: { x: 0, y: 0, z: 0, w: 1 },
        radius: 0.01 + Math.random() * 0.005,
        tracked: true
      }
    })

    jointsRef.current = simulatedJoints
    setJoints(simulatedJoints)
    setConfidence(0.7 + Math.random() * 0.3)

    detectHandGestures(simulatedJoints)

    animationRef.current = requestAnimationFrame(simulateHandTracking)
  }, [isTracking, detectHandGestures])

  const startSimulation = useCallback(() => {
    setIsTracking(true)
    animationRef.current = requestAnimationFrame(simulateHandTracking)
  }, [simulateHandTracking])

  const stopSimulation = useCallback(() => {
    setIsTracking(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const getJointPosition = useCallback((jointName) => {
    const joint = jointsRef.current.find(j => j.name === jointName)
    return joint?.position || { x: 0, y: 0, z: 0 }
  }, [])

  const getJointOrientation = useCallback((jointName) => {
    const joint = jointsRef.current.find(j => j.name === jointName)
    return joint?.orientation || { x: 0, y: 0, z: 0, w: 1 }
  }, [])

  const isJointTracked = useCallback((jointName) => {
    const joint = jointsRef.current.find(j => j.name === jointName)
    return joint?.tracked || false
  }, [])

  const getHandCenter = useCallback(() => {
    if (!jointsRef.current.length) return { x: 0, y: 0, z: 0 }

    const positions = jointsRef.current.map(j => j.position)
    return {
      x: positions.reduce((sum, p) => sum + p.x, 0) / positions.length,
      y: positions.reduce((sum, p) => sum + p.y, 0) / positions.length,
      z: positions.reduce((sum, p) => sum + p.z, 0) / positions.length
    }
  }, [])

  const getGestureHistory = useCallback(() => {
    return gestureHistoryRef.current
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
    hands,
    joints,
    gestures,
    confidence,
    pinchDistance,
    grabStrength,
    pointing,
    JOINT_NAMES,
    startTracking,
    stopTracking,
    extractJoints,
    updateHandData,
    startSimulation,
    stopSimulation,
    getJointPosition,
    getJointOrientation,
    isJointTracked,
    getHandCenter,
    getGestureHistory
  }
}
