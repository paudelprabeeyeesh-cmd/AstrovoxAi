import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

function generateVolumetricPanel(x, y, z, color) {
  return Array.from({ length: 8 }, (_, i) => ({
    x: x + (Math.random() - 0.5) * 60,
    y: y + (Math.random() - 0.5) * 40,
    z: z + (Math.random() - 0.5) * 20,
    size: Math.random() * 3 + 1,
    color,
    opacity: Math.random() * 0.5 + 0.2
  }))
}

export default function VolumetricUIPanel({ title, children, color = '#06b6d4' }) {
  const canvasRef = useRef(null)
  const [rotation, setRotation] = useState(0)
  const [panels, setPanels] = useState(() => [generateVolumetricPanel(0, 0, 0, color)])
  const [depth, setDepth] = useState(0.5)
  const [glow, setGlow] = useState(0.6)

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
      ctx.fillStyle = 'rgba(2, 4, 10, 0.15)'
      ctx.fillRect(0, 0, width, height)

      const cx = width / 2
      const cy = height / 2
      const time = frame * 0.01

      panels.forEach((panel, pi) => {
        const px = cx + Math.sin(time + pi * 1.5) * 30 * depth
        const py = cy + Math.cos(time + pi * 1.5) * 20 * depth
        const pz = Math.sin(time + pi) * 10 * depth

        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(rotation * Math.PI / 180 + pi * 0.3)

        const panelWidth = 120
        const panelHeight = 60
        const skew = pz * 0.5

        ctx.beginPath()
        ctx.moveTo(-panelWidth / 2, -panelHeight / 2)
        ctx.lineTo(panelWidth / 2 + skew, -panelHeight / 2)
        ctx.lineTo(panelWidth / 2, panelHeight / 2)
        ctx.lineTo(-panelWidth / 2 - skew, panelHeight / 2)
        ctx.closePath()
        ctx.fillStyle = `${color}11`
        ctx.fill()
        ctx.strokeStyle = `${color}66`
        ctx.lineWidth = 0.5
        ctx.stroke()

        panel.forEach(pt => {
          const px2 = pt.x * 0.3 + skew
          const py2 = pt.y * 0.3
          ctx.beginPath()
          ctx.arc(px2, py2, pt.size * (1 + pz * 0.1), 0, Math.PI * 2)
          ctx.fillStyle = `${color}${Math.floor(pt.opacity * 255 * glow).toString(16).padStart(2, '0')}`
          ctx.fill()
        })

        ctx.restore()
      })

      frame++
      requestAnimationFrame(draw)
    }
    draw()
  }, [panels, rotation, depth, glow, color])

  const addPanel = useCallback(() => {
    setPanels(prev => [...prev, generateVolumetricPanel((Math.random() - 0.5) * 40, (Math.random() - 0.5) * 30, Math.random() * 10, color)])
  }, [color])

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
        <h3 style={{ margin: 0, fontSize: '14px', color, letterSpacing: '1px', fontWeight: '600' }}>
          📦 3D VOLUMETRIC UI PANELS
        </h3>
        <button onClick={addPanel} style={{
          padding: '4px 10px', backgroundColor: color, color: '#02040a',
          border: 'none', borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px', fontWeight: '600'
        }}>+ Add Panel</button>
      </div>

      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Rotation</label>
          <input type="range" min="0" max="360" value={rotation} onChange={(e) => setRotation(Number(e.target.value))} style={{ width: '100px' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Depth</label>
          <input type="range" min="0" max="1" step="0.1" value={depth} onChange={(e) => setDepth(Number(e.target.value))} style={{ width: '100px' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Glow</label>
          <input type="range" min="0" max="1" step="0.1" value={glow} onChange={(e) => setGlow(Number(e.target.value))} style={{ width: '100px' }} />
        </div>
      </div>

      <div style={{ height: '280px', borderRadius: 'var(--astrovox-radius-md)', overflow: 'hidden', border: '1px solid var(--astrovox-border)', position: 'relative' }}>
        <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
        <div style={{
          position: 'absolute', bottom: '8px', left: '50%', transform: 'translateX(-50%)',
          fontSize: '9px', color: `${color}88`, fontFamily: 'monospace', letterSpacing: '1px'
        }}>{panels.length} VOLUMETRIC PANELS ACTIVE</div>
      </div>
    </div>
  )
}
