import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

export default function LightFieldRenderer() {
  const canvasRef = useRef(null)
  const [rays, setRays] = useState(12)
  const [refraction, setRefraction] = useState(0.7)
  const [waveMode, setWaveMode] = useState('interference')
  const [intensity, setIntensity] = useState(0.8)
  const [running, setRunning] = useState(true)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !running) return
    const ctx = canvas.getContext('2d')
    const w = canvas.width = canvas.offsetWidth * 2
    const h = canvas.height = canvas.offsetHeight * 2
    ctx.scale(2, 2)
    const width = w / 2
    const height = h / 2

    let frame = 0
    const draw = () => {
      if (!running) return
      ctx.fillStyle = 'rgba(2, 4, 10, 0.15)'
      ctx.fillRect(0, 0, width, height)

      const cx = width / 2
      const cy = height / 2
      const time = frame * 0.02

      const sourceX = cx - 80
      const sourceY = cy - 40

      ctx.beginPath()
      ctx.arc(sourceX, sourceY, 8, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(251, 191, 36, ${0.3 + intensity * 0.4})`
      ctx.fill()
      ctx.strokeStyle = '#fbbf24'
      ctx.lineWidth = 1.5
      ctx.stroke()

      for (let i = 0; i < rays; i++) {
        const angle = (i / rays) * Math.PI + Math.sin(time + i * 0.5) * 0.2 * refraction
        const length = 100 + Math.sin(time * 2 + i) * 30 * intensity
        const endX = sourceX + Math.cos(angle) * length
        const endY = sourceY + Math.sin(angle) * length

        const gradient = ctx.createLinearGradient(sourceX, sourceY, endX, endY)
        gradient.addColorStop(0, `rgba(251, 191, 36, ${0.6 * intensity})`)
        gradient.addColorStop(0.5, `rgba(6, 182, 212, ${0.3 * intensity})`)
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0)')

        ctx.beginPath()
        ctx.moveTo(sourceX, sourceY)
        ctx.lineTo(endX, endY)
        ctx.strokeStyle = gradient
        ctx.lineWidth = 1 + intensity * 0.5
        ctx.stroke()

        if (waveMode === 'interference') {
          for (let j = 1; j < 5; j++) {
            const t = j / 5
            const ix = sourceX + (endX - sourceX) * t
            const iy = sourceY + (endY - sourceY) * t
            ctx.beginPath()
            ctx.arc(ix, iy, 3 + Math.sin(time * 3 + j + i) * 2, 0, Math.PI * 2)
            ctx.fillStyle = `rgba(6, 182, 212, ${0.2 * intensity * (1 - t)})`
            ctx.fill()
          }
        }
      }

      if (waveMode === 'diffraction') {
        const gratingX = cx + 60
        for (let i = 0; i < 8; i++) {
          const y = cy - 60 + i * 15
          ctx.beginPath()
          ctx.moveTo(gratingX, y)
          ctx.lineTo(gratingX + 40 + Math.sin(time + i) * 10, y + Math.sin(time + i) * 5)
          ctx.strokeStyle = 'rgba(167, 139, 250, 0.4)'
          ctx.lineWidth = 1
          ctx.stroke()
        }
      }

      ctx.fillStyle = 'rgba(6, 182, 212, 0.1)'
      for (let i = 0; i < 5; i++) {
        const x = cx + 20 + i * 25
        const y = cy + 40
        ctx.beginPath()
        ctx.arc(x, y, 4 + Math.sin(time * 2 + i) * 2, 0, Math.PI * 2)
        ctx.fill()
      }

      frame++
      window.requestAnimationFrame(draw)
    }
    draw()
    return () => { running = false }
  }, [rays, refraction, waveMode, intensity, running])

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
          💡 LIGHT-FIELD RENDERER
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => setRunning(!running)} style={{
            padding: '4px 10px', backgroundColor: running ? '#34d399' : 'var(--astrovox-bg)',
            color: running ? '#02040a' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px'
          }}>{running ? '⏸ Pause' : '▶ Play'}</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Rays</label>
          <input type="range" min="4" max="32" value={rays} onChange={(e) => setRays(Number(e.target.value))} style={{ width: '120px' }} />
          <span style={{ fontSize: '9px', fontFamily: 'monospace', color: 'var(--astrovox-accent)' }}>{rays}</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Refraction</label>
          <input type="range" min="0" max="1" step="0.1" value={refraction} onChange={(e) => setRefraction(Number(e.target.value))} style={{ width: '120px' }} />
          <span style={{ fontSize: '9px', fontFamily: 'monospace', color: 'var(--astrovox-accent)' }}>{(refraction * 100).toFixed(0)}%</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Intensity</label>
          <input type="range" min="0" max="1" step="0.1" value={intensity} onChange={(e) => setIntensity(Number(e.target.value))} style={{ width: '120px' }} />
          <span style={{ fontSize: '9px', fontFamily: 'monospace', color: 'var(--astrovox-accent)' }}>{(intensity * 100).toFixed(0)}%</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Mode</label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {['interference', 'diffraction'].map(m => (
              <button key={m} onClick={() => setWaveMode(m)} style={{
                padding: '4px 8px', backgroundColor: waveMode === m ? '#a78bfa' : 'var(--astrovox-bg)',
                color: waveMode === m ? '#02040a' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '9px', textTransform: 'capitalize'
              }}>{m}</button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ height: '300px', borderRadius: 'var(--astrovox-radius-md)', overflow: 'hidden', border: '1px solid var(--astrovox-border)', backgroundColor: '#02040a' }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
      </div>
    </div>
  )
}
