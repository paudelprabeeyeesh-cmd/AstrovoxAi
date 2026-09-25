import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../../utils/holographic/HolographicConfig'

export function useNeuralInterface() {
  const [brainwaves, setBrainwaves] = useState([])
  const [consciousness, setConsciousness] = useState(0.5)
  const [focus, setFocus] = useState(0.7)
  const [meditation, setMeditation] = useState(0.3)
  const [thoughts, setThoughts] = useState([])
  const [isActive, setIsActive] = useState(false)
  const [neuralNoise, setNeuralNoise] = useState(0.1)
  const [connectivity, setConnectivity] = useState([])
  const animationRef = useRef(null)
  const sampleRate = HOLOGRAPHIC_CONFIG.neural.sampleRate
  const channels = HOLOGRAPHIC_CONFIG.neural.channels

  const frequencyBands = HOLOGRAPHIC_CONFIG.neural.frequencyBands

  const generateBrainwave = useCallback((time, frequency, amplitude) => {
    const noise = (Math.random() - 0.5) * neuralNoise
    const wave = Math.sin(2 * Math.PI * frequency * time) * amplitude
    const harmonic = Math.sin(2 * Math.PI * frequency * 2 * time) * amplitude * 0.5
    return wave + harmonic + noise
  }, [neuralNoise])

  const processEEGData = useCallback((rawData) => {
    const bands = frequencyBands
    const bandPowers = bands.map((freq, index) => {
      const bandWidth = index < bands.length - 1 ? bands[index + 1] - freq : 10
      const power = rawData.slice(0, 100).reduce((sum, value) => sum + Math.abs(value), 0) / 100
      return {
        frequency: freq,
        bandwidth: bandWidth,
        power: power * (1 + Math.random() * 0.2),
        coherence: 0.5 + Math.random() * 0.5
      }
    })

    setBrainwaves(bandPowers)

    const alpha = bandPowers[1]?.power || 0
    const beta = bandPowers[2]?.power || 0
    const theta = bandPowers[0]?.power || 0
    const delta = bandPowers[3]?.power || 0

    const meditationIndex = (alpha + theta) / (beta + delta + 0.001)
    const focusIndex = beta / (alpha + theta + 0.001)
    const consciousnessIndex = (bandPowers.reduce((sum, band) => sum + band.power, 0) / bandPowers.length) / 100

    setMeditation(Math.min(1, Math.max(0, meditationIndex)))
    setFocus(Math.min(1, Math.max(0, focusIndex)))
    setConsciousness(Math.min(1, Math.max(0, consciousnessIndex)))

    return bandPowers
  }, [frequencyBands])

  const simulateBrainActivity = useCallback((time) => {
    const rawData = []
    const samples = 256

    for (let i = 0; i < samples; i++) {
      const t = time + i / sampleRate
      let signal = 0

      signal += generateBrainwave(t, frequencyBands[0], 50)
      signal += generateBrainwave(t, frequencyBands[1], 30)
      signal += generateBrainwave(t, frequencyBands[2], 20)
      signal += generateBrainwave(t, frequencyBands[3], 40)
      signal += generateBrainwave(t, frequencyBands[4], 10)
      signal += generateBrainwave(t, frequencyBands[5], 5)

      signal += (Math.random() - 0.5) * neuralNoise * 50

      rawData.push(signal)
    }

    processEEGData(rawData)

    const connectivityMatrix = []
    for (let i = 0; i < channels; i++) {
      const row = []
      for (let j = 0; j < channels; j++) {
        const distance = Math.abs(i - j)
        const correlation = Math.exp(-distance / 10) * (0.5 + Math.random() * 0.5)
        const timeCorrelation = Math.sin(time + i * 0.1 + j * 0.1) * 0.3 + 0.7
        row.push(correlation * timeCorrelation)
      }
      connectivityMatrix.push(row)
    }

    setConnectivity(connectivityMatrix)

    if (Math.random() > 0.95) {
      const newThought = {
        id: Date.now() + Math.random(),
        content: generateThoughtContent(),
        timestamp: Date.now(),
        intensity: consciousness,
        clarity: focus,
        emotionalValence: Math.random() * 2 - 1
      }
      setThoughts(prev => [...prev.slice(-100), newThought])
    }

    animationRef.current = requestAnimationFrame(() => simulateBrainActivity(time + 1 / 60))
  }, [generateBrainwave, processEEGData, consciousness, focus, neuralNoise, channels, frequencyBands])

  const generateThoughtContent = useCallback(() => {
    const thoughts = [
      'Processing semantic associations...',
      'Analyzing contextual relationships...',
      'Activating memory recall pathways...',
      'Synthesizing multimodal data...',
      'Pattern recognition in progress...',
      'Optimizing neural pathways...',
      'Encoding episodic memory...',
      'Generating creative associations...',
      'Evaluating logical inference chains...',
      'Monitoring attentional focus...'
    ]
    return thoughts[Math.floor(Math.random() * thoughts.length)]
  }, [])

  const startNeuralInterface = useCallback(() => {
    setIsActive(true)
    animationRef.current = requestAnimationFrame(simulateBrainActivity)
  }, [simulateBrainActivity])

  const stopNeuralInterface = useCallback(() => {
    setIsActive(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const getBrainwaveAtFrequency = useCallback((frequency) => {
    const band = brainwaves.find(b => b.frequency <= frequency && b.frequency + b.bandwidth > frequency)
    return band?.power || 0
  }, [brainwaves])

  const getConnectivityBetween = useCallback((channel1, channel2) => {
    if (!connectivity.length || channel1 >= connectivity.length || channel2 >= connectivity[0].length) {
      return 0
    }
    return connectivity[channel1][channel2]
  }, [connectivity])

  const getThoughtStream = useCallback((limit = 10) => {
    return thoughts.slice(-limit)
  }, [thoughts])

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return {
    brainwaves,
    consciousness,
    focus,
    meditation,
    thoughts,
    connectivity,
    isActive,
    neuralNoise,
    frequencyBands,
    processEEGData,
    simulateBrainActivity,
    startNeuralInterface,
    stopNeuralInterface,
    getBrainwaveAtFrequency,
    getConnectivityBetween,
    getThoughtStream,
    setNeuralNoise
  }
}
