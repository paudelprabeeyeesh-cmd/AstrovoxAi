import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

export default function HolographicAssistantAvatar() {
  const canvasRef = useRef(null)
  const [mood, setMood] = useState('neutral')
  const [speaking, setSpeaking] = useState(false)
  const [energy, setEnergy] = useState(0.7)
  const [listening, setListening] = useState(false)

  const moods = ['neutral', 'happy', 'thinking', 'alert', 'calm']

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
    const draw = () => {
      ctx.fillStyle = 'rgba(2, 4, 10, 0.2)'
      ctx.fillRect(0, 0, width, height)

      const cx = width / 2
      const cy = height / 2 - 20
      const time = frame * 0.03

      ctx.beginPath()
      ctx.arc(cx, cy, 60 + Math.sin(time) * 3, 0, Math.PI * 2)
      const gradient = ctx.createRadialGradient(cx, cy, 10, cx, cy, 60)
      gradient.addColorStop(0, 'rgba(6, 182, 212, 0.1)')
      gradient.addColorStop(0.5, 'rgba(6, 182, 212, 0.05)')
      gradient.addColorStop(1, 'rgba(6, 182, 212, 0)')
      ctx.fillStyle = gradient
      ctx.fill()
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)'
      ctx.lineWidth = 1
      ctx.stroke()

      const eyeY = cy - 8
      const eyeSpacing = 16
      const blinkPhase = Math.sin(time * 0.5)
      const eyeHeight = blinkPhase > 0.95 ? 1 : 6
      const pupilOffsetX = listening ? Math.sin(time * 2) * 3 : 0
      const pupilOffsetY = mood === 'thinking' ? Math.sin(time * 1.5) * 2 : 0

      [{ x: cx - eyeSpacing, color: '#06b6d4' }, { x: cx + eyeSpacing, color: '#06b6d4' }].forEach(eye => {
        ctx.beginPath()
        ctx.ellipse(eye.x, eyeY, 10, eyeHeight, 0, 0, Math.PI * 2)
        ctx.fillStyle = 'rgba(6, 182, 212, 0.15)'
        ctx.fill()
        ctx.strokeStyle = eye.color
        ctx.lineWidth = 1.5
        ctx.stroke()

        if (eyeHeight > 2) {
          ctx.beginPath()
          ctx.arc(eye.x + pupilOffsetX, eyeY + pupilOffsetY, 3, 0, Math.PI * 2)
          ctx.fillStyle = '#06b6d4'
          ctx.fill()
        }
      })

      const mouthY = cy + 18
      ctx.beginPath()
      if (mood === 'happy' || speaking) {
        ctx.arc(cx, mouthY - 4, 10, 0.1 * Math.PI, 0.9 * Math.PI)
        ctx.strokeStyle = '#34d399'
        ctx.lineWidth = 2
        ctx.stroke()
      } else if (mood === 'thinking') {
        ctx.moveTo(cx - 8, mouthY + 4)
        ctx.lineTo(cx + 8, mouthY + 4)
        ctx.strokeStyle = '#fbbf24'
        ctx.lineWidth = 2
        ctx.stroke()
      } else {
        ctx.moveTo(cx - 6, mouthY)
        ctx.lineTo(cx + 6, mouthY)
        ctx.strokeStyle = 'rgba(6, 182, 212, 0.6)'
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      if (speaking) {
        for (let i = 0; i < 5; i++) {
          const angle = (i / 5) * Math.PI * 2 + time
          const r = 75 + Math.sin(time * 3 + i) * 5
          const x = cx + Math.cos(angle) * r
          const y = cy + Math.sin(angle) * r
          ctx.beginPath()
          ctx.arc(x, y, 2, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(6, 182, 212, ${0.3 + Math.sin(time * 2 + i) * 0.2})`
          ctx.fill()
        }
      }

      ctx.beginPath()
      ctx.arc(cx, cy, 80, 0, Math.PI * 2)
      ctx.strokeStyle = `rgba(6, 182, 212, ${0.1 + energy * 0.1})`
      ctx.lineWidth = 0.5
      ctx.setLineDash([4, 8])
      ctx.stroke()
      ctx.setLineDash([])

      for (let i = 0; i < 3; i++) {
        const scanY = ((time * 20 + i * 40) % height)
        ctx.beginPath()
        ctx.moveTo(0, scanY)
        ctx.lineTo(width, scanY)
        ctx.strokeStyle = `rgba(6, 182, 212, ${0.05 * energy})`
        ctx.lineWidth = 1
        ctx.stroke()
      }

      frame++
      requestAnimationFrame(draw)
    }
    draw()
  }, [mood, speaking, listening, energy])

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
          🛸 HOLOGRAPHIC ASSISTANT AVATAR
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => setSpeaking(!speaking)} style={{
            padding: '4px 10px', backgroundColor: speaking ? '#34d399' : 'var(--astrovox-bg)',
            color: speaking ? '#02040a' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px'
          }}>{speaking ? '🔊 Speaking' : '🔇 Mute'}</button>
          <button onClick={() => setListening(!listening)} style={{
            padding: '4px 10px', backgroundColor: listening ? '#fbbf24' : 'var(--astrovox-bg)',
            color: listening ? '#02040a' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px'
          }}>{listening ? '🎤 Listening' : '🎤 Listen'}</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', height: '280px' }}>
        <div style={{ flex: 1, position: 'relative', borderRadius: 'var(--astrovox-radius-md)', overflow: 'hidden', border: '1px solid var(--astrovox-border)', backgroundColor: '#02040a' }}>
          <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
          <div style={{
            position: 'absolute', bottom: '8px', left: '50%', transform: 'translateX(-50%)',
            fontSize: '9px', color: 'rgba(6, 182, 212, 0.5)', fontFamily: 'monospace', letterSpacing: '1px'
          }}>HOLOGRAM ACTIVE</div>
        </div>
        <div style={{ width: '160px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{
            padding: '12px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Mood</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {moods.map(m => (
                <button key={m} onClick={() => setMood(m)} style={{
                  padding: '4px 8px', backgroundColor: mood === m ? '#06b6d4' : 'transparent',
                  color: mood === m ? '#02040a' : 'var(--astrovox-text-muted)', border: `1px solid ${mood === m ? '#06b6d4' : 'var(--astrovox-border)'}`,
                  borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px', textTransform: 'capitalize'
                }}>{m}</button>
              ))}
            </div>
          </div>
          <div style={{
            padding: '12px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>Energy</div>
            <input type="range" min="0" max="1" step="0.1" value={energy} onChange={(e) => setEnergy(Number(e.target.value))} />
            <div style={{ fontSize: '10px', color: 'var(--astrovox-accent)', fontFamily: 'monospace', marginTop: '2px' }}>{(energy * 100).toFixed(0)}%</div>
          </div>
          <div style={{
            padding: '12px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)', fontSize: '10px', color: 'var(--astrovox-text-muted)'
          }}>
            Holographic projection rendered in real-time using canvas 2D. Eye tracking, mood states, and voice visualization.
          </div>
        </div>
      </div>
    </div>
  )
}
