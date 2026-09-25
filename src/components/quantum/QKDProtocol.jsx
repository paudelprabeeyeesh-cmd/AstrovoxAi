import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

function generateKeyPair(length) {
  const aliceBits = Array.from({ length }, () => Math.random() > 0.5 ? 1 : 0)
  const aliceBases = Array.from({ length }, () => Math.random() > 0.5 ? '+' : '×')
  const bobBits = aliceBits.map(() => Math.random() > 0.5 ? 1 : 0)
  const bobBases = Array.from({ length }, () => Math.random() > 0.5 ? '+' : '×')
  const sifted = aliceBases.map((ab, i) => ab === bobBases[i] ? { aliceBit: aliceBits[i], bobBit: bobBits[i], index: i } : null).filter(Boolean)
  const key = sifted.map(s => s.aliceBit).join('')
  const mismatches = sifted.filter(s => s.aliceBit !== s.bobBit).length
  const qber = sifted.length ? (mismatches / sifted.length) * 100 : 0
  return { aliceBits, aliceBases, bobBits, bobBases, sifted, key, qber, length }
}

export default function QKDProtocol() {
  const [keyLength, setKeyLength] = useState(32)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [evePresent, setEvePresent] = useState(false)
  const canvasRef = useRef(null)

  const runBB84 = useCallback(() => {
    setRunning(true)
    setTimeout(() => {
      const res = generateKeyPair(keyLength)
      if (evePresent) {
        const eveIntercept = res.sifted.map(s => ({
          ...s,
          bobBit: Math.random() > 0.5 ? s.aliceBit : (s.aliceBit ^ 1),
          eveIntercepted: true
        }))
        const mismatches = eveIntercept.filter(s => s.aliceBit !== s.bobBit).length
        setResult({ ...res, sifted: eveIntercept, qber: eveIntercept.length ? (mismatches / eveIntercept.length) * 100 : 0, eveIntercepted: true })
      } else {
        setResult(res)
      }
      setRunning(false)
    }, 1200)
  }, [keyLength, evePresent])

  useEffect(() => {
    if (!result) return
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const w = canvas.width = canvas.offsetWidth * 2
    const h = canvas.height = canvas.offsetHeight * 2
    ctx.scale(2, 2)
    const width = w / 2
    const height = h / 2
    ctx.fillStyle = 'rgba(2, 4, 10, 0.9)'
    ctx.fillRect(0, 0, width, height)

    const startY = 30
    const rowHeight = 22
    const colWidths = [40, 60, 60, 60, 80]
    const headers = ['#', 'Alice', 'Alice Basis', 'Bob', 'Bob Basis']
    let x = 10
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    headers.forEach((h, i) => {
      ctx.fillStyle = '#06b6d4'
      ctx.fillText(h, x + colWidths[i] / 2, 14)
      x += colWidths[i]
    })

    const rows = result.aliceBits.slice(0, 20)
    rows.forEach((bit, i) => {
      const y = startY + i * rowHeight
      x = 10
      ctx.fillStyle = 'rgba(226, 232, 240, 0.5)'
      ctx.fillText(i.toString(), x + colWidths[0] / 2, y)
      x += colWidths[0]
      ctx.fillStyle = '#f472b6'
      ctx.fillText(bit.toString(), x + colWidths[1] / 2, y)
      x += colWidths[1]
      ctx.fillStyle = result.aliceBases[i] === '+' ? '#34d399' : '#a78bfa'
      ctx.fillText(result.aliceBases[i], x + colWidths[2] / 2, y)
      x += colWidths[2]
      ctx.fillStyle = result.eveIntercepted && result.sifted.find(s => s.index === i)?.eveIntercepted ? '#ef4444' : '#fbbf24'
      ctx.fillText(result.bobBits[i].toString(), x + colWidths[3] / 2, y)
      x += colWidths[3]
      ctx.fillStyle = result.bobBases[i] === '+' ? '#34d399' : '#a78bfa'
      ctx.fillText(result.bobBases[i], x + colWidths[4] / 2, y)

      if (result.sifted.find(s => s.index === i)) {
        const s = result.sifted.find(s => s.index === i)
        ctx.fillStyle = s.aliceBit === s.bobBit ? '#34d399' : '#ef4444'
        ctx.beginPath()
        ctx.arc(x + colWidths[4] + 8, y - 4, 4, 0, Math.PI * 2)
        ctx.fill()
      }
    })
  }, [result])

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
          🔐 QUANTUM KEY DISTRIBUTION (BB84)
        </h3>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <input type="checkbox" checked={evePresent} onChange={(e) => setEvePresent(e.target.checked)} />
            Eve Present
          </label>
          <button onClick={runBB84} disabled={running} style={{
            padding: '6px 14px', backgroundColor: running ? 'var(--astrovox-border)' : '#34d399',
            color: running ? 'var(--astrovox-text-muted)' : '#02040a', border: 'none',
            borderRadius: 'var(--astrovox-radius-md)', cursor: running ? 'not-allowed' : 'pointer',
            fontSize: '11px', fontWeight: '600'
          }}>{running ? '🔒 Distributing...' : '🔒 Run BB84'}</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Key Length:</label>
        <input type="range" min="8" max="256" value={keyLength} onChange={(e) => setKeyLength(Number(e.target.value))} style={{ flex: 1 }} />
        <span style={{ fontSize: '11px', fontFamily: 'monospace', color: 'var(--astrovox-accent)' }}>{keyLength}</span>
      </div>

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{
            padding: '12px 16px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)', flex: '1 1 150px'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Shared Key</div>
            <div style={{ fontFamily: 'monospace', fontSize: '11px', color: '#34d399', wordBreak: 'break-all' }}>{result.key.slice(0, 32)}...</div>
          </div>
          <div style={{
            padding: '12px 16px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)', flex: '1 1 100px'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>QBER</div>
            <div style={{ fontSize: '18px', fontWeight: '700', color: result.qber > 11 ? '#ef4444' : '#34d399', fontFamily: 'monospace' }}>{result.qber.toFixed(2)}%</div>
          </div>
          <div style={{
            padding: '12px 16px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)', flex: '1 1 100px'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Sifted Bits</div>
            <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', fontFamily: 'monospace' }}>{result.sifted.length}</div>
          </div>
          <div style={{
            padding: '12px 16px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)', flex: '1 1 100px'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Security</div>
            <div style={{ fontSize: '14px', fontWeight: '600', color: result.qber > 11 ? '#ef4444' : '#34d399' }}>
              {result.qber > 11 ? '⚠️ Compromised' : '✅ Secure'}
            </div>
          </div>
        </motion.div>
      )}

      <div ref={canvasRef} style={{
        height: '240px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-md)',
        border: '1px solid var(--astrovox-border)', overflow: 'hidden'
      }} />

      <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', lineHeight: '1.5' }}>
        BB84 protocol simulation. Alice prepares qubits in random bases (+ rectilinear, × diagonal). Bob measures in random bases.
        Eve's presence introduces errors raising QBER above ~11% threshold. Sifted key shown in green (match) / red (mismatch).
      </div>
    </div>
  )
}
