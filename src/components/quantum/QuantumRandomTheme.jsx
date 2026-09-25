import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

function generateRandomBits(length) {
  return Array.from({ length }, () => Math.random() > 0.5 ? 1 : 0)
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export default function QuantumRandomTheme() {
  const [seeds, setSeeds] = useState(() => generateRandomBits(256))
  const [currentSeed, setCurrentSeed] = useState(() => generateRandomBits(64))
  const [themeName, setThemeName] = useState('Quantum Default')
  const [generating, setGenerating] = useState(false)
  const canvasRef = useRef(null)

  const quantumRandom = useCallback(() => {
    setGenerating(true)
    const newBits = generateRandomBits(256)
    setSeeds(newBits)
    const seedSlice = newBits.slice(0, 64)
    setCurrentSeed(seedSlice)

    const hue = seedSlice.slice(0, 8).reduce((a, b, i) => a + b * Math.pow(2, i), 0) % 360
    const sat = 60 + (seedSlice.slice(8, 16).reduce((a, b, i) => a + b * Math.pow(2, i), 0) % 40)
    const light = 40 + (seedSlice.slice(16, 24).reduce((a, b, i) => a + b * Math.pow(2, i), 0) % 30)
    const names = ['Quantum Nebula', 'Photon Drift', 'Entangled Haze', 'Superposition', 'Coherence', 'Qubit Storm', 'Wave Function', 'Hadamard Field', 'Pauli Matrix', 'Bell State']
    const name = names[seedSlice.slice(24, 32).reduce((a, b, i) => a + b * Math.pow(2, i), 0) % names.length]
    setThemeName(name)

    setTimeout(() => setGenerating(false), 600)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const w = canvas.width = canvas.offsetWidth * 2
    const h = canvas.height = canvas.offsetHeight * 2
    ctx.scale(2, 2)
    const width = w / 2
    const height = h / 2

    const hue = currentSeed.slice(0, 8).reduce((a, b, i) => a + b * Math.pow(2, i), 0) % 360

    ctx.fillStyle = `hsl(${hue}, 20%, 4%)`
    ctx.fillRect(0, 0, width, height)

    const gridSize = 20
    for (let x = 0; x < width; x += gridSize) {
      for (let y = 0; y < height; y += gridSize) {
        const idx = (x + y * width) % currentSeed.length
        const bit = currentSeed[idx]
        const alpha = bit ? 0.15 : 0.02
        ctx.fillStyle = `hsla(${hue + (x / width) * 60}, 70%, 50%, ${alpha})`
        ctx.fillRect(x, y, gridSize - 1, gridSize - 1)
      }
    }

    const centerX = width / 2
    const centerY = height / 2
    for (let i = 0; i < 12; i++) {
      const angle = (i / 12) * Math.PI * 2
      const r = 40 + currentSeed[i] * 20
      const x = centerX + Math.cos(angle) * r
      const y = centerY + Math.sin(angle) * r
      ctx.beginPath()
      ctx.arc(x, y, 3 + currentSeed[i + 12] * 4, 0, Math.PI * 2)
      ctx.fillStyle = `hsla(${hue + i * 30}, 80%, 60%, 0.6)`
      ctx.fill()
    }

    ctx.strokeStyle = `hsla(${hue}, 70%, 50%, 0.3)`
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.arc(centerX, centerY, 30, 0, Math.PI * 2)
    ctx.stroke()
  }, [currentSeed])

  return (
    <div style={{
      padding: '20px',
      backgroundColor: 'var(--astrovox-surface)',
      border: '1px solid var(--astrovox-border)',
      borderRadius: 'var(--astrovox-radius-lg)',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0, fontSize: '14px', color: 'var(--astrovox-accent)', letterSpacing: '1px', fontWeight: '600' }}>
          🎲 QUANTUM-RANDOM UI THEME
        </h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>{themeName}</span>
          <button onClick={quantumRandom} disabled={generating} style={{
            padding: '6px 14px', backgroundColor: generating ? 'var(--astrovox-border)' : '#a78bfa',
            color: generating ? 'var(--astrovox-text-muted)' : '#02040a', border: 'none',
            borderRadius: 'var(--astrovox-radius-md)', cursor: generating ? 'not-allowed' : 'pointer',
            fontSize: '11px', fontWeight: '600'
          }}>
            {generating ? '⚛️ Measuring...' : '⚛️ New Theme'}
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', height: '200px' }}>
        <div ref={canvasRef} style={{ flex: 1, borderRadius: 'var(--astrovox-radius-md)', overflow: 'hidden', border: '1px solid var(--astrovox-border)' }} />
        <div style={{ width: '180px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{
            padding: '12px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Entropy Source</div>
            <div style={{ fontFamily: 'monospace', fontSize: '11px', color: 'var(--astrovox-accent)', wordBreak: 'break-all' }}>
              {currentSeed.slice(0, 16).map(b => b).join('')}...
            </div>
          </div>
          <div style={{
            padding: '12px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Randomness Quality</div>
            <div style={{ display: 'flex', gap: '2px', flexWrap: 'wrap' }}>
              {currentSeed.slice(0, 32).map((bit, i) => (
                <div key={i} style={{
                  width: '8px', height: '8px', borderRadius: '1px',
                  backgroundColor: bit ? '#a78bfa' : 'var(--astrovox-border)'
                }} />
              ))}
            </div>
          </div>
          <div style={{
            padding: '12px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)', fontSize: '10px', color: 'var(--astrovox-text-muted)'
          }}>
            Simulated quantum random number generator using superposition of 256 qubits.
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        {currentSeed.slice(0, 64).map((bit, i) => (
          <div key={i} style={{
            width: '6px', height: '16px', borderRadius: '1px',
            backgroundColor: bit ? '#a78bfa' : 'var(--astrovox-border)',
            transition: 'background-color 0.3s'
          }} />
        ))}
      </div>
    </div>
  )
}
