import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../../utils/holographic/HolographicConfig'

export function useQuantumState() {
  const [qubits, setQubits] = useState([])
  const [isSimulating, setIsSimulating] = useState(false)
  const [coherence, setCoherence] = useState(1)
  const [entanglement, setEntanglement] = useState([])
  const [measurements, setMeasurements] = useState([])
  const [superposition, setSuperposition] = useState(true)
  const [quantumNoise, setQuantumNoise] = useState(HOLOGRAPHIC_CONFIG.quantum.measurementNoise)
  const animationRef = useRef(null)
  const numQubits = HOLOGRAPHIC_CONFIG.quantum.qubits

  const initializeQubits = useCallback(() => {
    const initialized = []
    for (let i = 0; i < numQubits; i++) {
      initialized.push({
        index: i,
        amplitude: 1 / Math.sqrt(2),
        phase: Math.random() * Math.PI * 2,
        measured: false,
        value: Math.random() > 0.5 ? 1 : 0,
        coherence: 1,
        entanglement: []
      })
    }
    setQubits(initialized)
    return initialized
  }, [numQubits])

  const applyGate = useCallback((gate, targetQubits) => {
    setQubits(prev => prev.map(qubit => {
      if (!targetQubits.includes(qubit.index)) return qubit

      let newAmplitude = qubit.amplitude
      let newPhase = qubit.phase

      switch (gate) {
        case 'H':
          newAmplitude = qubit.amplitude / Math.sqrt(2)
          newPhase = qubit.phase
          break
        case 'X':
          newAmplitude = qubit.measured ? 1 - qubit.value : qubit.amplitude
          break
        case 'Y':
          newAmplitude = qubit.amplitude * (qubit.measured ? (qubit.value ? -1 : 1) : 1)
          newPhase = qubit.phase + (qubit.measured ? (qubit.value ? Math.PI : 0) : 0)
          break
        case 'Z':
          if (qubit.measured && qubit.value === 1) {
            newPhase = qubit.phase + Math.PI
          }
          break
        case 'S':
          newPhase = qubit.phase + Math.PI / 2
          break
        case 'T':
          newPhase = qubit.phase + Math.PI / 4
          break
        case 'RX':
          newAmplitude = qubit.amplitude * Math.cos(qubit.phase / 2)
          newPhase = qubit.phase + Math.sin(qubit.phase / 2)
          break
        case 'RY':
          newAmplitude = qubit.amplitude * Math.sin(qubit.phase / 2)
          newPhase = qubit.phase + Math.cos(qubit.phase / 2)
          break
        case 'RZ':
          newPhase = qubit.phase + qubit.amplitude
          break
        default:
          break
      }

      return {
        ...qubit,
        amplitude: Math.max(0, Math.min(1, newAmplitude)),
        phase: newPhase % (Math.PI * 2),
        measured: false
      }
    }))
  }, [])

  const createEntanglement = useCallback((qubit1, qubit2) => {
    setEntanglement(prev => {
      if (prev.some(e => (e.q1 === qubit1 && e.q2 === qubit2) || (e.q1 === qubit2 && e.q2 === qubit1))) {
        return prev
      }

      const newEntanglement = {
        id: Date.now(),
        q1: qubit1,
        q2: qubit2,
        strength: HOLOGRAPHIC_CONFIG.quantum.entanglementStrength,
        type: Math.random() > 0.5 ? 'bell' : 'ghz',
        phase: Math.random() * Math.PI * 2
      }

      setQubits(prevQubits => prevQubits.map(q => {
        if (q.index === qubit1 || q.index === qubit2) {
          return {
            ...q,
            entanglement: [...q.entanglement, newEntanglement.id]
          }
        }
        return q
      }))

      return [...prev, newEntanglement]
    })
  }, [])

  const measure = useCallback((qubitIndex) => {
    setQubits(prev => prev.map(qubit => {
      if (qubit.index !== qubitIndex) return qubit

      const probability = qubit.amplitude ** 2
      const measuredValue = Math.random() < probability ? 1 : 0
      const noise = (Math.random() - 0.5) * quantumNoise
      const actualValue = Math.max(0, Math.min(1, measuredValue + noise))

      const measurement = {
        id: Date.now(),
        qubit: qubitIndex,
        value: actualValue,
        probability,
        timestamp: Date.now(),
        collapse: true
      }

      setMeasurements(prevMeas => [...prevMeas.slice(-100), measurement])

      return {
        ...qubit,
        measured: true,
        value: actualValue,
        amplitude: actualValue,
        coherence: qubit.coherence * HOLOGRAPHIC_CONFIG.quantum.coherenceTime
      }
    }))
  }, [quantumNoise])

  const measureAll = useCallback(() => {
    qubits.forEach((_, index) => {
      setTimeout(() => measure(index), index * 100)
    })
  }, [qubits, measure])

  const reset = useCallback(() => {
    setQubits(prev => prev.map(qubit => ({
      ...qubit,
      amplitude: 1 / Math.sqrt(2),
      phase: Math.random() * Math.PI * 2,
      measured: false,
      value: Math.random() > 0.5 ? 1 : 0,
      coherence: 1
    })))
    setMeasurements([])
    setEntanglement(prev => prev.filter(() => Math.random() > 0.5))
    setCoherence(1)
  }, [])

  const simulateDecoherence = useCallback((time) => {
    const decoherenceRate = HOLOGRAPHIC_CONFIG.quantum.superpositionDecay

    setQubits(prev => prev.map(qubit => {
      const newCoherence = qubit.coherence * Math.exp(-decoherenceRate * time)
      const decoherence = 1 - newCoherence
      const randomPhase = (Math.random() - 0.5) * decoherence * Math.PI

      return {
        ...qubit,
        coherence: Math.max(0, newCoherence),
        phase: qubit.phase + randomPhase,
        amplitude: qubit.measured ? qubit.value : qubit.amplitude * newCoherence
      }
    }))

    setCoherence(prev => Math.max(0, prev - decoherenceRate * time))
  }, [])

  const simulateQuantum = useCallback((time) => {
    if (!isSimulating) return

    const phase = time * 0.001

    setQubits(prev => prev.map(qubit => {
      if (qubit.measured) return qubit

      const interference = Math.sin(phase + qubit.phase) * 0.1
      const noise = (Math.random() - 0.5) * quantumNoise

      return {
        ...qubit,
        phase: (qubit.phase + 0.01 + noise) % (Math.PI * 2),
        amplitude: Math.max(0, Math.min(1, qubit.amplitude + interference))
      }
    }))

    simulateDecoherence(time)

    animationRef.current = requestAnimationFrame(simulateQuantum)
  }, [isSimulating, quantumNoise, simulateDecoherence])

  const startSimulation = useCallback(() => {
    setIsSimulating(true)
    initializeQubits()
    animationRef.current = requestAnimationFrame(simulateQuantum)
  }, [initializeQubits, simulateQuantum])

  const stopSimulation = useCallback(() => {
    setIsSimulating(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const getQubitState = useCallback((index) => {
    return qubits.find(q => q.index === index)
  }, [qubits])

  const getEntangledQubits = useCallback((qubitIndex) => {
    const qubit = qubits.find(q => q.index === qubitIndex)
    if (!qubit) return []

    return qubit.entanglement.map(eId => {
      const ent = entanglement.find(e => e.id === eId)
      if (!ent) return null

      const otherQubitIndex = ent.q1 === qubitIndex ? ent.q2 : ent.q1
      return {
        qubit: otherQubitIndex,
        strength: ent.strength,
        type: ent.type
      }
    }).filter(Boolean)
  }, [qubits, entanglement])

  const applySuperposition = useCallback(() => {
    setQubits(prev => prev.map(qubit => ({
      ...qubit,
      amplitude: 1 / Math.sqrt(2),
      phase: Math.random() * Math.PI * 2,
      measured: false,
      coherence: 1
    })))
    setSuperposition(true)
  }, [])

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return {
    qubits,
    isSimulating,
    coherence,
    entanglement,
    measurements,
    superposition,
    quantumNoise,
    initializeQubits,
    applyGate,
    createEntanglement,
    measure,
    measureAll,
    reset,
    simulateDecoherence,
    startSimulation,
    stopSimulation,
    getQubitState,
    getEntangledQubits,
    applySuperposition,
    setQuantumNoise
  }
}
