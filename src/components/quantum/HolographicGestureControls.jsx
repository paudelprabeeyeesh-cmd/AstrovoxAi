import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

export default function HolographicGestureControls() {
  const canvasRef = useRef(null)
  const [gesture, setGesture] = useState('idle')
  const [sensitivity, setSensitivity] = useState(0.6)
  const [trail, setTrail] = useState([])
  const [history, setHistory] = useState([])
  const [active, setActive] = useState(false)

  const gestures = ['idle', 'swipe_left', 'swipe_right', 'swipe_up', 'swipe_down', 'pinch', 'rotate', 'tap']

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const w = canvas.width = canvas.offsetWidth * 2
    const h = canvas.height = canvas.offsetHeight * 2
    ctx.scale(2, 2)
    const width = w / 2
    const height = h / 2

    let frame = 0
    let particles = Array.from({ length: 30 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 1
    }))

    const draw = () => {
      ctx.fillStyle = 'rgba(2, 4, 10, 0.2)'
      ctx.fillRect(0, 0, width, height)

      particles.forEach(p => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) p.x = width
        if (p.x > width) p.x = 0
        if (p.y < 0) p.y = height
        if (p.y > height) p.y = 0

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(6, 182, 212, 0.3)'
        ctx.fill()
      })

      for (let i = 0; i < particles.length - 1; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 60) {
            ctx.beginPath()
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.strokeStyle = `rgba(6, 182, 212, ${0.15 * (1 - dist / 60)})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      }

      if (active && trail.length > 1) {
        ctx.beginPath()
        ctx.moveTo(trail[0].x, trail[0].y)
        for (let i = 1; i < trail.length; i++) {
          ctx.lineTo(trail[i].x, trail[i].y)
        }
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.6)'
        ctx.lineWidth = 2
        ctx.lineCap = 'round'
        ctx.stroke()

        const last = trail[trail.length - 1]
        ctx.beginPath()
        ctx.arc(last.x, last.y, 8 + Math.sin(frame * 0.1) * 2, 0, Math.PI * 2)
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)'
        ctx.lineWidth = 1
        ctx.stroke()
      }

      ctx.font = '10px monospace'
      ctx.textAlign = 'center'
      ctx.fillStyle = 'rgba(6, 182, 212, 0.6)'
      ctx.fillText(`GESTURE: ${gesture.toUpperCase()}`, width / 2, height - 20)

      frame++
      window.requestAnimationFrame(draw)
    }
    draw()
  }, [trail, gesture, active])

  const handlePointerMove = useCallback((e) => {
    if (!active) return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    setTrail(prev => {
      const next = [...prev, { x, y }]
      return next.length > 50 ? next.slice(-50) : next
    })
  }, [active])

  const detectGesture = useCallback(() => {
    if (trail.length < 10) return
    const first = trail[0]
    const last = trail[trail.length - 1]
    const dx = last.x - first.x
    const dy = last.y - first.y
    const dist = Math.sqrt(dx * dx + dy * dy)

    if (dist < 20) {
      setGesture('tap')
    } else if (Math.abs(dx) > Math.abs(dy)) {
      setGesture(dx > 0 ? 'swipe_right' : 'swipe_left')
    } else {
      setGesture(dy > 0 ? 'swipe_down' : 'swipe_up')
    }
    setHistory(prev => [...prev.slice(-9), { gesture: gesture, timestamp: Date.now() }])
    setTimeout(() => setGesture('idle'), 1000)
  }, [trail, gesture])

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
          🖐️ HOLOGRAPHIC GESTURE CONTROLS
        </h3>
        <button onClick={() => setActive(!active)} style={{
          padding: '6px 14px', backgroundColor: active ? '#34d399' : 'var(--astrovox-bg)',
          color: active ? '#02040a' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-md)', cursor: 'pointer', fontSize: '11px', fontWeight: '600'
        }}>{active ? '✓ Active' : 'Activate'}</button>
      </div>

      <div style={{ display: 'flex', gap: '12px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Sensitivity</label>
          <input type="range" min="0" max="1" step="0.1" value={sensitivity} onChange={(e) => setSensitivity(Number(e.target.value))} style={{ width: '120px' }} />
        </div>
        <button onClick={detectGesture} style={{
          padding: '6px 14px', backgroundColor: 'var(--astrovox-primary)', color: 'var(--astrovox-bg)',
          border: 'none', borderRadius: 'var(--astrovox-radius-md)', cursor: 'pointer', fontSize: '11px', fontWeight: '600'
        }}>Detect Gesture</button>
      </div>

      <div style={{ height: '200px', borderRadius: 'var(--astrovox-radius-md)', overflow: 'hidden', border: '1px solid var(--astrovox-border)', backgroundColor: '#02040a', position: 'relative' }}>
        <canvas
          ref={canvasRef}
          style={{ width: '100%', height: '100%', display: 'block', cursor: active ? 'crosshair' : 'default' }}
          onPointerMove={handlePointerMove}
          onPointerDown={() => setActive(true)}
          onPointerUp={() => setActive(false)}
        />
        {!active && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: 'var(--astrovox-text-muted)', fontSize: '12px', pointerEvents: 'none'
          }}>Click and drag to perform gestures</div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {gestures.map(g => (
          <span key={g} style={{
            padding: '3px 8px', borderRadius: '4px', fontSize: '9px', textTransform: 'uppercase',
            backgroundColor: gesture === g ? 'var(--astrovox-primary)' : 'var(--astrovox-bg)',
            color: gesture === g ? 'var(--astrovox-bg)' : 'var(--astrovox-text-muted)',
            border: `1px solid ${gesture === g ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`
          }}>{g.replace('_', ' ')}</span>
        ))}
      </div>

      {history.length > 0 && (
        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          {history.map((h, i) => (
            <span key={i} style={{
              padding: '2px 6px', borderRadius: '3px', fontSize: '9px', fontFamily: 'monospace',
              backgroundColor: 'var(--astrovox-bg)', color: 'var(--astrovox-text-muted)', border: '1px solid var(--astrovox-border)'
              }}>{h.gesture}</span>
          ))}
        </div>
      )}
    </div>
  )
}
