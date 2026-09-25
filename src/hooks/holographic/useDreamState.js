import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../utils/holographic/HolographicConfig'

export function useDreamState() {
  const [isDreaming, setIsDreaming] = useState(false)
  const [dreamPhase, setDreamPhase] = useState('awake')
  const [dreamClarity, setDreamClarity] = useState(0.1)
  const [lucidityLevel, setLucidityLevel] = useState(0)
  const [dreamScenes, setDreamScenes] = useState([])
  const [dreamNarrative, setDreamNarrative] = useState('')
  const [dreamSymbols, setDreamSymbols] = useState([])
  const [isLucidAssistantActive, setIsLucidAssistantActive] = useState(false)
  const animationRef = useRef(null)

  const dreamPhases = ['awake', 'drowsy', 'light_sleep', 'rem', 'deep_sleep', 'lucid', 'hypnagogic']
  const dreamStages = ['initiation', 'immersion', 'exploration', 'transformation', 'resolution']

  const generateDreamScene = useCallback((phase, clarity) => {
    const scenes = {
      hypnagogic: generateHypnagogicScene,
      light_sleep: generateLightSleepScene,
      rem: generateREMScene,
      deep_sleep: generateDeepSleepScene,
      lucid: generateLucidScene
    }

    const generator = scenes[phase] || generateREMScene
    return generator(clarity)
  }, [])

  const generateHypnagogicScene = (clarity) => {
    const shapes = ['geometric', 'organic', 'abstract', 'symbolic']
    const colors = ['#a78bfa', '#f472b6', '#06b6d4', '#67e8f9']
    const shape = shapes[Math.floor(Math.random() * shapes.length)]
    const color = colors[Math.floor(Math.random() * colors.length)]

    return {
      id: Date.now(),
      type: 'hypnagogic',
      shape,
      color,
      opacity: clarity * 0.6,
      morphSpeed: 0.2 + Math.random() * 0.3,
      transformationRate: 0.1 + Math.random() * 0.2,
      elements: Array.from({ length: 10 }, (_, i) => ({
        id: i,
        x: Math.random(),
        y: Math.random(),
        size: 20 + Math.random() * 80,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.02,
        alpha: 0.3 + Math.random() * 0.7
      }))
    }
  }

  const generateLightSleepScene = (clarity) => {
    return {
      id: Date.now(),
      type: 'light_sleep',
      environment: generateEnvironment('semi_lucid'),
      characters: Array.from({ length: 3 }, () => generateCharacter()),
      opacity: clarity * 0.7,
      coherence: 0.5 + Math.random() * 0.3,
      logicDefiance: Math.random() * 0.4
    }
  }

  const generateREMScene = (clarity) => {
    return {
      id: Date.now(),
      type: 'rem',
      environment: generateEnvironment('fully_dreaming'),
      characters: Array.from({ length: 5 }, () => generateCharacter()),
      plot: generateDreamPlot(),
      emotionalTone: Math.random() * 2 - 1,
      vividness: clarity,
      opacity: clarity * 0.8,
      logicDefiance: 0.6 + Math.random() * 0.4
    }
  }

  const generateDeepSleepScene = (clarity) => {
    return {
      id: Date.now(),
      type: 'deep_sleep',
      abstract: true,
      elements: Array.from({ length: 20 }, (_, i) => ({
        id: i,
        form: ['blob', 'wave', 'pulse', 'void'][Math.floor(Math.random() * 4)],
        color: HOLOGRAPHIC_COLORS.dream,
        intensity: Math.random() * 0.3,
        movement: Math.random() * 0.1
      })),
      opacity: clarity * 0.4,
      coherence: 0.2
    }
  }

  const generateLucidScene = (clarity) => {
    return {
      id: Date.now(),
      type: 'lucid',
      environment: generateEnvironment('controlled'),
      characters: Array.from({ length: 2 }, () => generateCharacter(true)),
      controls: ['gravity', 'weather', 'time', 'characters', 'physics'],
      activeControls: [],
      lucidityStability: lucidityLevel,
      opacity: clarity * 0.9,
      coherence: 0.8 + Math.random() * 0.2
    }
  }

  const generateEnvironment = (type) => {
    const environments = {
      semi_lucid: ['room', 'corridor', 'outdoor_familiar', 'outdoor_unknown'],
      fully_dreaming: ['fantasy', 'surreal', 'realistic', 'abstract', 'hybrid'],
      controlled: ['custom', 'memory_palace', 'training_simulation', 'creative_space']
    }

    const envList = environments[type] || environments.fully_dreaming
    const envType = envList[Math.floor(Math.random() * envList.length)]

    return {
      type: envType,
      details: generateEnvironmentDetails(envType),
      lighting: type === 'controlled' ? 'user_defined' : 'dream_ambient',
      physics: type === 'controlled' ? 'user_defined' : 'dream_physics'
    }
  }

  const generateEnvironmentDetails = (envType) => {
    const details = {
      room: ['familiar_room', 'unknown_room', 'childhood_room', 'surreal_room'],
      corridor: ['endless', 'looping', 'branching', 'shifting'],
      outdoor_familiar: ['home_street', 'school', 'workplace', 'park'],
      outdoor_unknown: ['alien_landscape', 'floating_islands', 'crystalline', 'organic'],
      fantasy: ['castle', 'enchanted_forest', 'floating_city', 'underwater'],
      surreal: ['impossible_geometry', 'melting_objects', 'shifting_dimensions'],
      realistic: ['detailed_realism', 'slightly_off', 'hyper_realistic'],
      abstract: ['pure_color', 'geometric_patterns', 'mathematical', 'emotional'],
      hybrid: ['mixed_realities', 'dream_bleed', 'portal_connected'],
      custom: ['user_designated']
    }

    const typeDetails = details[envType] || details.realistic
    return {
      primary: typeDetails[Math.floor(Math.random() * typeDetails.length)],
      secondary: typeDetails[Math.floor(Math.random() * typeDetails.length)],
      atmosphere: generateAtmosphere()
    }
  }

  const generateAtmosphere = () => {
    const atmospheres = ['serene', 'mysterious', 'tense', 'joyful', 'melancholic', 'ethereal', 'chaotic']
    return atmospheres[Math.floor(Math.random() * atmospheres.length)]
  }

  const generateCharacter = (lucid = false) => {
    return {
      id: Date.now() + Math.random(),
      type: lucid ? 'guide' : ['stranger', 'familiar', 'animal', 'entity', 'self'][Math.floor(Math.random() * 5)],
      appearance: generateAppearance(),
      behavior: generateBehavior(),
      dialogue: lucid ? null : generateDialogue(),
      emotionalState: Math.random() * 2 - 1,
      lucidityAware: lucid
    }
  }

  const generateAppearance = () => {
    const appearances = ['vague_outline', 'detailed', 'shifting', 'symbolic', 'archetypal']
    return appearances[Math.floor(Math.random() * appearances.length)]
  }

  const generateBehavior = () => {
    const behaviors = ['friendly', 'neutral', 'mysterious', 'elusive', 'interactive', 'observing']
    return behaviors[Math.floor(Math.random() * behaviors.length)]
  }

  const generateDialogue = () => {
    const dialogues = [
      '...remember...',
      'look deeper...',
      'what are you searching for?',
      'the answer is within...',
      'follow the light...',
      'wake up...',
      'stay with me...',
      'explore...'
    ]
    return dialogues[Math.floor(Math.random() * dialogues.length)]
  }

  const generateDreamPlot = () => {
    const plots = [
      'journey_quest',
      'transformation',
      'resolution',
      'exploration',
      'confrontation',
      'reunion',
      'escape',
      'discovery'
    ]
    return {
      type: plots[Math.floor(Math.random() * plots.length)],
      stages: dreamStages,
      currentStage: 0,
      branching: Math.random() > 0.7
    }
  }

  const animateDream = useCallback((time) => {
    if (!isDreaming) return

    const newClarity = dreamClarity + (Math.random() - 0.5) * 0.05
    const stabilizedClarity = Math.max(0, Math.min(1, newClarity))
    setDreamClarity(stabilizedClarity)

    if (Math.random() > 0.98 && stabilizedClarity > 0.5) {
      const currentPhase = dreamPhase
      const scene = generateDreamScene(currentPhase, stabilizedClarity)
      setDreamScenes(prev => [...prev.slice(-50), scene])
    }

    if (stabilizedClarity > 0.7 && isLucidAssistantActive) {
      const newLucidity = lucidityLevel + (Math.random() - 0.3) * 0.05
      setLucidityLevel(Math.max(0, Math.min(1, newLucidity)))
    }

    animationRef.current = requestAnimationFrame(animateDream)
  }, [isDreaming, dreamClarity, dreamPhase, isLucidAssistantActive, lucidityLevel, generateDreamScene])

  const enterDreamState = useCallback(async (initialPhase = 'light_sleep') => {
    setIsDreaming(true)
    setDreamPhase(initialPhase)

    const initialScene = generateDreamScene(initialPhase, dreamClarity)
    setDreamScenes([initialScene])

    animationRef.current = requestAnimationFrame(animateDream)
  }, [dreamClarity, generateDreamScene, animateDream])

  const exitDreamState = useCallback(() => {
    setIsDreaming(false)
    setIsLucidAssistantActive(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
    setDreamPhase('awake')
    setDreamClarity(0.1)
    setLucidityLevel(0)
  }, [])

  const activateLucidAssistant = useCallback(() => {
    setIsLucidAssistantActive(true)
  }, [])

  const deactivateLucidAssistant = useCallback(() => {
    setIsLucidAssistantActive(false)
  }, [])

  const stabilizeLucidity = useCallback(() => {
    if (!isDreaming) return

    const newLucidity = lucidityLevel + 0.1
    setLucidityLevel(Math.min(1, newLucidity))
    setDreamClarity(prev => Math.min(1, prev + 0.1))

    setDreamNarrative('Stabilizing lucidity... Reality checks passed. You are dreaming.')
  }, [isDreaming, lucidityLevel])

  const performRealityCheck = useCallback(() => {
    if (!isDreaming) return false

    const checks = ['hand_inspection', 'text_stability', 'mirror_reflection', 'light_switch', 'breath_control']
    const check = checks[Math.floor(Math.random() * checks.length)]
    const passed = lucidityLevel > 0.3

    setDreamNarrative(passed ? `Reality check (${check}): PASSED - You are dreaming.` : `Reality check (${check}): Inconclusive.`)

    if (passed) {
      const newLucidity = lucidityLevel + 0.15
      setLucidityLevel(Math.min(1, newLucidity))
    }

    return passed
  }, [isDreaming, lucidityLevel])

  const navigateMemoryPalace = useCallback((room) => {
    if (!isDreaming || dreamPhase !== 'lucid') return null

    const roomScene = {
      id: Date.now(),
      type: 'memory_palace_room',
      room,
      contents: generateMemoryRoomContents(room),
      opacity: dreamClarity * 0.9,
      coherence: 0.9
    }

    setDreamScenes(prev => [...prev, roomScene])
    setDreamNarrative(`Entering memory palace: ${room}`)

    return roomScene
  }, [isDreaming, dreamPhase, dreamClarity])

  const generateMemoryRoomContents = (room) => {
    return {
      memories: Array.from({ length: 5 }, () => ({
        id: Date.now() + Math.random(),
        type: 'episodic',
        age: Math.floor(Math.random() * 365),
        emotionalWeight: Math.random() * 2 - 1,
        vividness: 0.5 + Math.random() * 0.5
      })),
      associations: Math.floor(Math.random() * 10),
      accessibility: 0.5 + Math.random() * 0.5
    }
  }

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return {
    isDreaming,
    dreamPhase,
    dreamClarity,
    lucidityLevel,
    dreamScenes,
    dreamNarrative,
    dreamSymbols,
    isLucidAssistantActive,
    enterDreamState,
    exitDreamState,
    activateLucidAssistant,
    deactivateLucidAssistant,
    stabilizeLucidity,
    performRealityCheck,
    navigateMemoryPalace,
    generateDreamScene,
    setDreamClarity,
    setDreamPhase
  }
}
