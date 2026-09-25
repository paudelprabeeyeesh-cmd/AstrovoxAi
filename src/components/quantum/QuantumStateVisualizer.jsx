import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

function complexToRGB(amp) {
  const re = amp.real ?? amp.re ?? 0
  const im = amp.imag ?? amp.im ?? 0
  const mag = Math.sqrt(re * re + im * im)
  const phase = Math.atan2(im, re)
  const hue = ((phase + Math.PI) / (2 * Math.PI)) * 360
  const lightness = 30 + mag * 50
  return { mag, phase, hue, lightness, color: `hsl(${hue}, 80%, ${lightness}%)` }
}

export default function QuantumStateVisualizer() {
  const canvasRef = useRef(null)
  const [qubits, setQubits] = useState(2)
  const [basis, setBasis] = useState('computational')
  const [stateVector, setStateVector] = useState([
    { label: '|00⟩', amp: { real: 1, imag: 0 }, prob: 1 },
    { label: '|01⟩', amp: { real: 0, imag: 0 }, prob: 0 },
    { label: '|10⟩', amp: { real: 0, imag: 0 }, prob: 0 },
    { label: '|11⟩', amp: { real: 0, imag: 0 }, prob: 0 }
  ])
  const [active, setActive] = useState('none')
  const [animation, setAnimation] = useState(true)

  const applyHadamard = useCallback((target) => {
    setStateVector(prev => {
      const newState = [...prev]
      const dim = 2 ** qubits
      for (let base = 0; base < dim; base += 2) {
        const i0 = base
        const i1 = base + 1
        const a0 = newState[i0].amp
        const a1 = newState[i1].amp
        newState[i0] = { label: newState[i0].label, amp: { real: (a0.real + a1.real) / Math.sqrt(2), imag: (a0.imag + a1.imag) / Math.sqrt(2) }, prob: 0 }
        newState[i1] = { label: newState[i1].label, amp: { real: (a0.real - a1.real) / Math.sqrt(2), imag: (a0.imag - a1.imag) / Math.sqrt(2) }, prob: 0 }
      }
      return newState.map(s => ({ ...s, prob: Math.sqrt((s.amp.real ** 2) + (s.amp.imag ** 2)) }))
    })
  }, [qubits])

  const applyPauliX = useCallback((target) => {
    setStateVector(prev => {
      const newState = [...prev]
      const dim = 2 ** qubits
      for (let base = 0; base < dim; base += 2) {
        const i0 = base
        const i1 = base + 1
        const tmp = { ...newState[i0] }
        newState[i0] = { ...newState[i1] }
        newState[i1] = tmp
      }
      return newState
    })
  }, [qubits])

  const randomize = useCallback(() => {
    setStateVector(prev => {
      const amps = prev.map(() => ({
        real: (Math.random() - 0.5) * 2,
        imag: (Math.random() - 0.5) * 2
      }))
      const mag = Math.sqrt(amps.reduce((sum, a) => sum + (a.real ** 2 + a.imag ** 2), 0))
      const normalized = amps.map(a => ({ real: a.real / mag, imag: a.imag / mag }))
      return prev.map((s, i) => ({
        ...s,
        amp: normalized[i],
        prob: Math.sqrt(normalized[i].real ** 2 + normalized[i].imag ** 2)
      }))
    })
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const width = canvas.width = canvas.offsetWidth * 2
    const height = canvas.height = canvas.offsetHeight * 2
    ctx.scale(2, 2)
    const w = width / 2
    const h = height / 2

    let frame = 0
    let animating = true
    const draw = () => {
      if (!animating) return
      ctx.fillStyle = 'rgba(2, 4, 10, 0.15)'
      ctx.fillRect(0, 0, w, h)

      const cx = w / 2
      const cy = h / 2
      const radius = Math.min(w, h) * 0.35

      ctx.beginPath()
      ctx.arc(cx, cy, radius, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.3)'
      ctx.lineWidth = 1
      ctx.stroke()

      ctx.beginPath()
      ctx.arc(cx, cy, radius * 0.5, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.2)'
      ctx.stroke()

      ctx.beginPath()
      ctx.moveTo(cx - radius, cy)
      ctx.lineTo(cx + radius, cy)
      ctx.moveTo(cx, cy - radius)
      ctx.lineTo(cx, cy + radius)
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.1)'
      ctx.stroke()

      stateVector.forEach((s, i) => {
        const angle = (i / stateVector.length) * Math.PI * 2 - Math.PI / 2
        const x = cx + Math.cos(angle + frame * 0.01) * radius * 0.8
        const y = cy + Math.sin(angle + frame * 0.01) * radius * 0.8
        const rgb = complexToRGB(s.amp)
        const size = 4 + rgb.mag * 8

        ctx.beginPath()
        ctx.arc(x, y, size, 0, Math.PI * 2)
        ctx.fillStyle = rgb.color
        ctx.fill()
        ctx.strokeStyle = 'rgba(255,255,255,0.3)'
        ctx.lineWidth = 0.5
        ctx.stroke()

        ctx.fillStyle = 'rgba(226, 232, 240, 0.7)'
        ctx.font = '9px monospace'
        ctx.textAlign = 'center'
        ctx.fillText(s.label, x, y - size - 6)
      })

      if (active === 'bloch') {
        const bx = cx + Math.cos(frame * 0.02) * radius * 0.3
        const by = cy + Math.sin(frame * 0.02) * radius * 0.3
        ctx.beginPath()
        ctx.arc(bx, by, 6, 0, Math.PI * 2)
        ctx.fillStyle = '#fbbf24'
        ctx.fill()
        ctx.strokeStyle = 'rgba(251, 191, 36, 0.5)'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(bx, by, 12 + Math.sin(frame * 0.05) * 4, 0, Math.PI * 2)
        ctx.stroke()
      }

      frame++
      window.requestAnimationFrame(draw)
    }
    draw()
    return () => { animating = false }
  }, [stateVector, active, animation])

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
          🔮 QUANTUM STATE VISUALIZER
        </h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <input type="checkbox" checked={animation} onChange={(e) => setAnimation(e.target.checked)} />
            Animate
          </label>
          <button onClick={() => setActive(active === 'bloch' ? 'none' : 'bloch')} style={{
            padding: '4px 10px', backgroundColor: active === 'bloch' ? '#fbbf24' : 'var(--astrovox-bg)',
            color: active === 'bloch' ? '#02040a' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px'
          }}>Bloch</button>
          <button onClick={randomize} style={{
            padding: '4px 10px', backgroundColor: 'var(--astrovox-primary)', color: 'var(--astrovox-bg)',
            border: 'none', borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px'
          }}>Randomize</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px' }}>
        <button onClick={() => applyHadamard(0)} style={{
          padding: '6px 12px', backgroundColor: '#06b6d433', color: '#06b6d4', border: '1px solid #06b6d466',
          borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '11px', fontFamily: 'monospace'
        }}>H</button>
        <button onClick={() => applyPauliX(0)} style={{
          padding: '6px 12px', backgroundColor: '#f472b633', color: '#f472b6', border: '1px solid #f472b666',
          borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '11px', fontFamily: 'monospace'
        }}>X</button>
      </div>

      <div style={{ display: 'flex', gap: '12px', height: '300px' }}>
        <div style={{ flex: 1, position: 'relative', borderRadius: 'var(--astrovox-radius-md)', overflow: 'hidden', border: '1px solid var(--astrovox-border)' }}>
          <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
        </div>
        <div style={{ width: '200px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {stateVector.map((s, i) => {
            const rgb = complexToRGB(s.amp)
            return (
              <div key={i} style={{
                padding: '10px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
                border: '1px solid var(--astrovox-border)', fontSize: '11px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span style={{ fontFamily: 'monospace', color: 'var(--astrovox-accent)' }}>{s.label}</span>
                  <span style={{ fontFamily: 'monospace', color: 'var(--astrovox-text-muted)' }}>{(rgb.mag * 100).toFixed(1)}%</span>
                </div>
                <div style={{ height: '4px', backgroundColor: 'var(--astrovox-border)', borderRadius: '2px', overflow: 'hidden' }}>
                  <motion.div animate={{ width: `${rgb.mag * 100}%` }} transition={{ duration: 0.5 }} style={{
                    height: '100%', backgroundColor: rgb.color, borderRadius: '2px'
                  }} />
                </div>
                <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', marginTop: '2px', fontFamily: 'monospace' }}>
                  {s.amp.real.toFixed(3)} {s.amp.imag >= 0 ? '+' : ''}{s.amp.imag.toFixed(3)}i
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
