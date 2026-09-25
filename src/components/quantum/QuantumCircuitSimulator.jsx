import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

const GATES = {
  H: { name: 'Hadamard', symbol: 'H', color: '#06b6d4', matrix: [[1/Math.sqrt(2), 1/Math.sqrt(2)], [1/Math.sqrt(2), -1/Math.sqrt(2)]] },
  X: { name: 'Pauli-X', symbol: 'X', color: '#f472b6', matrix: [[0, 1], [1, 0]] },
  Y: { name: 'Pauli-Y', symbol: 'Y', color: '#a78bfa', matrix: [[0, -1j], [1j, 0]] },
  Z: { name: 'Pauli-Z', symbol: 'Z', color: '#34d399', matrix: [[1, 0], [0, -1]] },
  CNOT: { name: 'CNOT', symbol: '⊕', color: '#fbbf24', matrix: null }
}

function multiplyMatrices(a, b) {
  const result = Array(a.length).fill(0).map(() => Array(b[0].length).fill(0))
  for (let i = 0; i < a.length; i++) {
    for (let j = 0; j < b[0].length; j++) {
      for (let k = 0; k < b.length; k++) {
        result[i][j] += a[i][k] * b[k][j]
      }
    }
  }
  return result
}

function applyGate(state, gate, target, control) {
  if (gate === 'CNOT' && control !== undefined) {
    const newState = [...state]
    for (let i = 0; i < state.length; i++) {
      const bits = i.toString(2).padStart(2, '0').split('').map(Number)
      if (bits[control] === 1) {
        bits[target] = bits[target] ^ 1
        const flipped = parseInt(bits.join(''), 2)
        newState[flipped] = { amp: state[i].amp, prob: state[i].prob }
      }
    }
    return newState
  }
  const mat = GATES[gate].matrix
  const newState = [...state]
  const dim = mat.length
  for (let base = 0; base < state.length; base += dim) {
    const block = state.slice(base, base + dim).map(s => s.amp)
    const result = Array(dim).fill(0)
    for (let i = 0; i < dim; i++) {
      for (let j = 0; j < dim; j++) {
        result[i] += mat[i][j] * block[j]
      }
    }
    for (let i = 0; i < dim; i++) {
      newState[base + i] = { amp: result[i], prob: Math.abs(result[i]) ** 2 }
    }
  }
  return newState
}

function initialState() {
  return [
    { amp: 1, prob: 1, label: '|00⟩' },
    { amp: 0, prob: 0, label: '|01⟩' },
    { amp: 0, prob: 0, label: '|10⟩' },
    { amp: 0, prob: 0, label: '|11⟩' }
  ]
}

export default function QuantumCircuitSimulator() {
  const [circuit, setCircuit] = useState([])
  const [selectedGate, setSelectedGate] = useState('H')
  const [selectedQubit, setSelectedQubit] = useState(0)
  const [controlQubit, setControlQubit] = useState(1)
  const [state, setState] = useState(initialState())
  const [running, setRunning] = useState(false)
  const [history, setHistory] = useState([])

  const addGate = useCallback(() => {
    if (selectedGate === 'CNOT') {
      setCircuit(prev => [...prev, { gate: 'CNOT', target: selectedQubit, control: controlQubit, id: Date.now() }])
    } else {
      setCircuit(prev => [...prev, { gate: selectedGate, target: selectedQubit, id: Date.now() }])
    }
  }, [selectedGate, selectedQubit, controlQubit])

  const runCircuit = useCallback(() => {
    setRunning(true)
    let current = initialState()
    let h = []
    for (const step of circuit) {
      current = applyGate(current, step.gate, step.target, step.control)
      h.push({ ...step, result: [...current] })
    }
    setState(current)
    setHistory(h)
    setTimeout(() => setRunning(false), 800)
  }, [circuit])

  const resetCircuit = useCallback(() => {
    setCircuit([])
    setState(initialState())
    setHistory([])
  }, [])

  const removeGate = useCallback((id) => {
    setCircuit(prev => prev.filter(g => g.id !== id))
  }, [])

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
          ⚛️ QUANTUM CIRCUIT SIMULATOR
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={addGate} style={{
            padding: '6px 14px', backgroundColor: 'var(--astrovox-primary)', color: 'var(--astrovox-bg)',
            border: 'none', borderRadius: 'var(--astrovox-radius-md)', cursor: 'pointer', fontSize: '11px', fontWeight: '600'
          }}>Add Gate</button>
          <button onClick={runCircuit} style={{
            padding: '6px 14px', backgroundColor: '#34d399', color: '#02040a',
            border: 'none', borderRadius: 'var(--astrovox-radius-md)', cursor: 'pointer', fontSize: '11px', fontWeight: '600'
          }}>▶ Run</button>
          <button onClick={resetCircuit} style={{
            padding: '6px 14px', backgroundColor: 'transparent', color: 'var(--astrovox-text-muted)',
            border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', cursor: 'pointer', fontSize: '11px'
          }}>Reset</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Gate</label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {Object.entries(GATES).map(([key, g]) => (
              <button key={key} onClick={() => setSelectedGate(key)} style={{
                padding: '6px 12px', backgroundColor: selectedGate === key ? g.color : 'var(--astrovox-bg)',
                color: selectedGate === key ? '#02040a' : 'var(--astrovox-text)', border: `1px solid ${g.color}33`,
                borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '12px', fontWeight: '600', fontFamily: 'monospace'
              }}>{g.symbol}</button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Target Qubit</label>
          <div style={{ display: 'flex', gap: '4px' }}>
            {[0, 1].map(q => (
              <button key={q} onClick={() => setSelectedQubit(q)} style={{
                padding: '6px 12px', backgroundColor: selectedQubit === q ? 'var(--astrovox-primary)' : 'var(--astrovox-bg)',
                color: selectedQubit === q ? 'var(--astrovox-bg)' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '12px'
              }}>Q{q}</button>
            ))}
          </div>
        </div>
        {selectedGate === 'CNOT' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Control Qubit</label>
            <div style={{ display: 'flex', gap: '4px' }}>
              {[0, 1].filter(q => q !== selectedQubit).map(q => (
                <button key={q} onClick={() => setControlQubit(q)} style={{
                  padding: '6px 12px', backgroundColor: controlQubit === q ? '#fbbf24' : 'var(--astrovox-bg)',
                  color: controlQubit === q ? '#02040a' : 'var(--astrovox-text)', border: '1px solid #fbbf2433',
                  borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '12px'
                }}>Q{q}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Circuit</label>
        <div style={{
          backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)',
          padding: '16px', minHeight: '120px', position: 'relative'
        }}>
          {circuit.length === 0 && (
            <div style={{ color: 'var(--astrovox-text-muted)', fontSize: '12px', textAlign: 'center', padding: '20px' }}>
              No gates added. Select a gate and qubit, then click "Add Gate".
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {circuit.map((step, idx) => {
              const gateDef = GATES[step.gate]
              return (
                <motion.div key={step.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} style={{
                  display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 12px',
                  backgroundColor: 'var(--astrovox-surface)', borderRadius: 'var(--astrovox-radius-sm)', border: '1px solid var(--astrovox-border)'
                }}>
                  <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace', minWidth: '24px' }}>t{idx}</span>
                  <span style={{ color: gateDef.color, fontWeight: '700', fontFamily: 'monospace', fontSize: '14px' }}>{gateDef.symbol}</span>
                  <span style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>→ Q{step.target}{step.control !== undefined ? ` (ctrl: Q${step.control})` : ''}</span>
                  <button onClick={() => removeGate(step.id)} style={{
                    marginLeft: 'auto', padding: '2px 8px', backgroundColor: 'transparent', color: '#ef4444',
                    border: '1px solid #ef444433', borderRadius: '4px', cursor: 'pointer', fontSize: '10px'
                  }}>✕</button>
                </motion.div>
              )
            })}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Quantum State</label>
        <div style={{
          backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)',
          padding: '16px', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px'
        }}>
          {state.map((s, i) => (
            <div key={i} style={{
              padding: '12px', backgroundColor: 'var(--astrovox-surface)', borderRadius: 'var(--astrovox-radius-sm)',
              border: '1px solid var(--astrovox-border)', textAlign: 'center'
            }}>
              <div style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--astrovox-accent)', marginBottom: '4px' }}>{s.label}</div>
              <motion.div animate={{ scale: running ? [1, 1.05, 1] : 1 }} transition={{ duration: 0.3 }} style={{
                height: '60px', backgroundColor: s.prob > 0 ? `rgba(6, 182, 212, ${s.prob})` : 'transparent',
                borderRadius: 'var(--astrovox-radius-sm)', border: `1px solid ${s.prob > 0 ? 'rgba(6, 182, 212, 0.3)' : 'var(--astrovox-border)'}`,
                display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: '4px'
              }}>
                {s.prob > 0 && <span style={{ fontSize: '10px', color: 'var(--astrovox-text)', fontFamily: 'monospace' }}>{(s.prob * 100).toFixed(1)}%</span>}
              </motion.div>
            </div>
          ))}
        </div>
      </div>

      {history.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Execution Trace</label>
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {history.map((h, i) => (
              <div key={i} style={{
                padding: '4px 8px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-sm)', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text-muted)'
              }}>
                t{i}: {h.result.map(r => r.label).join(' ')}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
