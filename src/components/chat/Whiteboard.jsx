import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

const COLORS = ['#06b6d4', '#f472b6', '#34d399', '#fbbf24', '#ef4444', '#8b5cf6']

export default function Whiteboard({ onClose, onSave }) {
  const canvasRef = useRef(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [color, setColor] = useState(COLORS[0])
  const [lineWidth, setLineWidth] = useState(2)
  const [tool, setTool] = useState('pen')
  const [history, setHistory] = useState([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [showToolbar, setShowToolbar] = useState(true)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const rect = canvas.parentElement.getBoundingClientRect()
    canvas.width = rect.width
    canvas.height = rect.height || 400
    ctx.fillStyle = 'var(--astrovox-bg, #02040a)'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    saveState()
  }, [])

  const saveState = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
    setHistory(prev => [...prev.slice(0, historyIndex + 1), imageData])
    setHistoryIndex(prev => prev + 1)
  }, [historyIndex])

  const startDrawing = useCallback((e) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    ctx.beginPath()
    ctx.moveTo(x, y)
    setIsDrawing(true)
  }, [])

  const draw = useCallback((e) => {
    if (!isDrawing) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    ctx.lineTo(x, y)
    ctx.strokeStyle = color
    ctx.lineWidth = lineWidth
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.stroke()
  }, [isDrawing, color, lineWidth])

  const stopDrawing = useCallback(() => {
    if (isDrawing) {
      setIsDrawing(false)
      saveState()
    }
  }, [isDrawing, saveState])

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      setHistoryIndex(prev => prev - 1)
      ctx.putImageData(history[historyIndex - 1], 0, 0)
    }
  }, [history, historyIndex])

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const canvas = canvasRef.current
      if (!canvas) return
      const ctx = canvas.getContext('2d')
      setHistoryIndex(prev => prev + 1)
      ctx.putImageData(history[historyIndex + 1], 0, 0)
    }
  }, [history, historyIndex])

  const clear = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--astrovox-bg').trim() || '#02040a'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    saveState()
  }, [saveState])

  const handleSave = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dataUrl = canvas.toDataURL('image/png')
    onSave?.({
      type: 'whiteboard',
      src: dataUrl,
      width: canvas.width,
      height: canvas.height,
      savedAt: new Date().toISOString()
    })
  }, [onSave])

  return (
    <div
      style={{
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--astrovox-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Icon name="edit" size={18} style={{ color: 'var(--astrovox-primary)' }} />
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Whiteboard</span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={handleSave} style={{ ...buttonStyle }}>Save</button>
          <button onClick={onClose} style={{ ...buttonStyle }}>Close</button>
        </div>
      </div>

      {showToolbar && (
        <div
          style={{
            padding: '8px 16px',
            borderBottom: '1px solid var(--astrovox-border)',
            display: 'flex',
            gap: '8px',
            alignItems: 'center',
            flexWrap: 'wrap'
          }}
        >
          <div style={{ display: 'flex', gap: '4px' }}>
            {COLORS.map(c => (
              <button
                key={c}
                onClick={() => setColor(c)}
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: c,
                  border: color === c ? '2px solid white' : '1px solid var(--astrovox-border)',
                  cursor: 'pointer'
                }}
                aria-label={`Color ${c}`}
              />
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: '8px' }}>
            <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Size:</span>
            <input
              type="range"
              min="1"
              max="10"
              value={lineWidth}
              onChange={(e) => setLineWidth(Number(e.target.value))}
              style={{ width: '60px' }}
              aria-label="Line width"
            />
          </div>
          <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
            <button onClick={undo} style={{ ...buttonStyle }} aria-label="Undo">Undo</button>
            <button onClick={redo} style={{ ...buttonStyle }} aria-label="Redo">Redo</button>
            <button onClick={clear} style={{ ...buttonStyle }} aria-label="Clear">Clear</button>
          </div>
        </div>
      )}

      <canvas
        ref={canvasRef}
        onMouseDown={startDrawing}
        onMouseMove={draw}
        onMouseUp={stopDrawing}
        onMouseLeave={stopDrawing}
        style={{
          flex: 1,
          cursor: 'crosshair',
          backgroundColor: 'var(--astrovox-bg)',
          touchAction: 'none'
        }}
      />
    </div>
  )
}

const buttonStyle = {
  padding: '4px 10px',
  backgroundColor: 'var(--astrovox-surface-hover)',
  color: 'var(--astrovox-text)',
  border: '1px solid var(--astrovox-border)',
  borderRadius: 'var(--astrovox-radius-sm)',
  cursor: 'pointer',
  fontSize: '11px',
  fontFamily: 'inherit'
}
