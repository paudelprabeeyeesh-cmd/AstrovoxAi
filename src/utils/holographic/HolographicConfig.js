export const HOLOGRAPHIC_CONFIG = {
  glitch: {
    intensity: 0.15,
    frequency: 0.02,
    chromaticAberration: 2.5,
    scanlineOpacity: 0.08,
    noiseAmount: 0.04
  },
  depth: {
    near: 0.1,
    far: 100,
    layers: 8,
    parallaxFactor: 0.3,
    blurTransition: 0.5
  },
  lightField: {
    resolution: 128,
    apertureSize: 0.03,
    focalLength: 0.05,
    samplingDensity: 4
  },
  volumetric: {
    voxelSize: 0.1,
    density: 0.7,
    absorption: 0.3,
    emission: 0.5,
    maxDepth: 50
  },
  hologram: {
    refreshRate: 60,
    persistence: 0.92,
    diffraction: 0.08,
    interference: 0.12,
    speckleReduction: 0.6
  },
  gesture: {
    smoothing: 0.3,
    confidence: 0.7,
    recognitionWindow: 500,
    gestureLibrary: ['swipe', 'pinch', 'rotate', 'wave', 'point', 'grab', 'release', 'push']
  },
  xr: {
    defaultMode: 'inline',
    requiredFeatures: ['local-floor', 'hand-tracking'],
    optionalFeatures: ['eye-tracking', 'layers', 'light-estimation'],
    handConfidence: 0.6,
    eyeTrackingSmoothing: 0.2
  },
  neural: {
    sampleRate: 256,
    channels: 64,
    frequencyBands: [0.5, 4, 8, 13, 30, 100],
    visualizationSmoothing: 0.15,
    thoughtDecodingThreshold: 0.75
  },
  quantum: {
    qubits: 8,
    coherenceTime: 100,
    superpositionDecay: 0.01,
    entanglementStrength: 0.9,
    measurementNoise: 0.05
  }
}

export const HOLOGRAPHIC_COLORS = {
  primary: '#06b6d4',
  secondary: '#f472b6',
  accent: '#67e8f9',
  tertiary: '#a78bfa',
  success: '#34d399',
  warning: '#fbbf24',
  error: '#ef4444',
  hologram: 'rgba(6, 182, 212, 0.85)',
  hologramGlow: 'rgba(6, 182, 212, 0.3)',
  depthFar: 'rgba(6, 182, 212, 0.05)',
  depthNear: 'rgba(103, 232, 249, 0.9)',
  neural: '#22d3ee',
  quantum: '#c084fc',
  consciousness: '#f472b6',
  dream: '#a78bfa'
}

export const HOLOGRAPHIC_LAYOUTS = {
  floatingPanel: {
    backdropFilter: 'blur(20px) saturate(180%)',
    background: 'rgba(15, 23, 42, 0.75)',
    border: '1px solid rgba(6, 182, 212, 0.3)',
    borderRadius: '16px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(6, 182, 212, 0.15)',
    transform: 'perspective(1000px) rotateY(-5deg) rotateX(2deg)',
    transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s ease'
  },
  hologramCard: {
    background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(244, 114, 182, 0.05) 100%)',
    border: '1px solid rgba(6, 182, 212, 0.2)',
    borderRadius: '12px',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(12px)'
  },
  hologramButton: {
    background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2) 0%, rgba(6, 182, 212, 0.1) 100%)',
    border: '1px solid rgba(6, 182, 212, 0.4)',
    borderRadius: '8px',
    color: '#67e8f9',
    boxShadow: '0 0 15px rgba(6, 182, 212, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
  },
  hologramInput: {
    background: 'rgba(15, 23, 42, 0.6)',
    border: '1px solid rgba(6, 182, 212, 0.3)',
    borderRadius: '8px',
    color: '#e2e8f0',
    boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)',
    outline: 'none'
  }
}
