import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

export default function WebGLHolographicChat() {
  const canvasRef = useRef(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [scanlineIntensity, setScanlineIntensity] = useState(0.15)
  const [chromaticAberration, setChromaticAberration] = useState(0.8)
  const [depth, setDepth] = useState(0.6)
  const [hologramActive, setHologramActive] = useState(true)

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
    let activeHologram = true
    const draw = () => {
      if (!activeHologram) return
      ctx.fillStyle = 'rgba(2, 4, 10, 0.95)'
      ctx.fillRect(0, 0, width, height)

      for (let y = 0; y < height; y += 3) {
        ctx.fillStyle = `rgba(6, 182, 212, ${scanlineIntensity * 0.3})`
        ctx.fillRect(0, y, width, 1)
      }

      messages.forEach((msg, i) => {
        const y = 40 + i * 60
        const isUser = msg.role === 'user'
        const x = isUser ? width - 220 : 20
        const baseColor = isUser ? '#f472b6' : '#06b6d4'

        const depthOffset = depth * 10
        const chromOffset = chromaticAberration * 3

        ctx.font = '11px monospace'
        ctx.textAlign = isUser ? 'right' : 'left'

        ctx.fillStyle = `rgba(244, 114, 182, ${0.3 * depth})`
        ctx.fillText(msg.content, x + chromOffset, y + depthOffset)
        ctx.fillStyle = `rgba(6, 182, 212, ${0.3 * depth})`
        ctx.fillText(msg.content, x - chromOffset, y - depthOffset)

        ctx.fillStyle = baseColor
        ctx.fillText(msg.content, x, y)

        const boxWidth = Math.min(ctx.measureText(msg.content).width + 20, 200)
        ctx.strokeStyle = `${baseColor}44`
        ctx.lineWidth = 0.5
        ctx.strokeRect(x - 4, y - 14, isUser ? -boxWidth : boxWidth, 22)
      })

      if (hologramActive) {
        const shimmerY = (frame * 1.5) % height
        ctx.fillStyle = `rgba(6, 182, 212, ${0.02 * (1 - shimmerY / height)})`
        ctx.fillRect(0, shimmerY, width, 20)
      }

      frame++
      window.requestAnimationFrame(draw)
    }
    draw()
    return () => { activeHologram = false }
  }, [messages, scanlineIntensity, chromaticAberration, depth, hologramActive])

  const handleSend = useCallback((e) => {
    e.preventDefault()
    if (!input.trim()) return
    setMessages(prev => [...prev, { role: 'user', content: input.trim(), id: Date.now() }])
    setInput('')
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Holographic response received. Quantum channel stable.', id: Date.now() + 1 }])
    }, 600)
  }, [input])

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
          🌐 WebGL HOLOGRAPHIC CHAT RENDERER
        </h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <input type="checkbox" checked={hologramActive} onChange={(e) => setHologramActive(e.target.checked)} />
            Hologram
          </label>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Scanlines</label>
          <input type="range" min="0" max="1" step="0.05" value={scanlineIntensity} onChange={(e) => setScanlineIntensity(Number(e.target.value))} style={{ width: '100px' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Chromatic</label>
          <input type="range" min="0" max="2" step="0.1" value={chromaticAberration} onChange={(e) => setChromaticAberration(Number(e.target.value))} style={{ width: '100px' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Depth</label>
          <input type="range" min="0" max="1" step="0.05" value={depth} onChange={(e) => setDepth(Number(e.target.value))} style={{ width: '100px' }} />
        </div>
      </div>

      <div style={{ height: '320px', borderRadius: 'var(--astrovox-radius-md)', overflow: 'hidden', border: '1px solid var(--astrovox-border)', position: 'relative' }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
        <div style={{
          position: 'absolute', top: '8px', left: '50%', transform: 'translateX(-50%)',
          fontSize: '9px', color: 'rgba(6, 182, 212, 0.5)', fontFamily: 'monospace', letterSpacing: '2px'
        }}>HOLOGRAPHIC CHAT RENDERER</div>
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Send holographic message..."
          style={{
            flex: 1, padding: '10px 14px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-full)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'monospace',
            outline: 'none'
          }}
        />
        <button type="submit" style={{
          padding: '10px 20px', backgroundColor: '#06b6d4', color: '#02040a', border: 'none',
          borderRadius: 'var(--astrovox-radius-full)', cursor: 'pointer', fontSize: '11px', fontWeight: '700', fontFamily: 'monospace'
        }}>TRANSMIT</button>
      </form>
    </div>
  )
}
