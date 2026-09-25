import { useState, useCallback, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

function generateBenchmarkData() {
  const algorithms = [
    { name: 'Shor\'s Factoring', qubits: '4,096', speedup: 'Exponential', status: 'theoretical', description: 'Integer factorization' },
    { name: 'Grover\'s Search', qubits: '1,024', speedup: 'Quadratic', status: 'simulated', description: 'Unstructured search' },
    { name: 'VQE Chemistry', qubits: '256', speedup: 'Polynomial', status: 'experimental', description: 'Molecular simulation' },
    { name: 'QAOA Optimization', qubits: '512', speedup: 'Heuristic', status: 'experimental', description: 'Combinatorial optimization' },
    { name: 'HHL Linear Systems', qubits: '128', speedup: 'Logarithmic', status: 'theoretical', description: 'Linear equation solving' }
  ]
  const metrics = algorithms.map(a => ({
    ...a,
    fidelity: 85 + Math.random() * 15,
    circuitDepth: Math.floor(Math.random() * 500) + 50,
    gateCount: Math.floor(Math.random() * 2000) + 100,
    runtime: (Math.random() * 10 + 0.1).toFixed(3),
    coherenceTime: (Math.random() * 100 + 10).toFixed(1)
  }))
  const advantageScore = metrics.reduce((sum, m) => sum + m.fidelity * (m.speedup === 'Exponential' ? 3 : m.speedup === 'Quadratic' ? 2 : 1), 0) / metrics.length
  return { algorithms: metrics, advantageScore, totalQubits: '5,888', avgFidelity: (metrics.reduce((s, m) => s + m.fidelity, 0) / metrics.length).toFixed(1) }
}

export default function QuantumBenchmarkDashboard() {
  const [data, setData] = useState(() => generateBenchmarkData())
  const [view, setView] = useState('overview')
  const [running, setRunning] = useState(false)

  const runBenchmark = useCallback(() => {
    setRunning(true)
    setTimeout(() => {
      setData(generateBenchmarkData())
      setRunning(false)
    }, 1500)
  }, [])

  const statusColor = (status) => ({
    theoretical: '#a78bfa',
    simulated: '#06b6d4',
    experimental: '#fbbf24'
  }[status] || '#64748b')

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
          📊 QUANTUM ADVANTAGE BENCHMARK
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          {['overview', 'fidelity', 'depth'].map(v => (
            <button key={v} onClick={() => setView(v)} style={{
              padding: '4px 10px', backgroundColor: view === v ? 'var(--astrovox-primary)' : 'var(--astrovox-bg)',
              color: view === v ? 'var(--astrovox-bg)' : 'var(--astrovox-text)', border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-sm)', cursor: 'pointer', fontSize: '10px', textTransform: 'capitalize'
            }}>{v}</button>
          ))}
          <button onClick={runBenchmark} disabled={running} style={{
            padding: '6px 14px', backgroundColor: running ? 'var(--astrovox-border)' : '#34d399',
            color: running ? 'var(--astrovox-text-muted)' : '#02040a', border: 'none',
            borderRadius: 'var(--astrovox-radius-md)', cursor: running ? 'not-allowed' : 'pointer',
            fontSize: '11px', fontWeight: '600'
          }}>{running ? '⚡ Benchmarking...' : '⚡ Run'}</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px' }}>
        {[
          { label: 'Total Qubits', value: data.totalQubits, icon: 'zap', color: '#06b6d4' },
          { label: 'Avg Fidelity', value: `${data.avgFidelity}%`, icon: 'activity', color: '#34d399' },
          { label: 'Advantage Score', value: data.advantageScore.toFixed(1), icon: 'trending-up', color: '#fbbf24' },
          { label: 'Algorithms', value: data.algorithms.length.toString(), icon: 'cpu', color: '#f472b6' }
        ].map(stat => (
          <motion.div key={stat.label} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{
            padding: '16px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-lg)',
            border: '1px solid var(--astrovox-border)'
          }}>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>{stat.label}</div>
            <div style={{ fontSize: '20px', fontWeight: '700', color: stat.color, fontFamily: 'monospace' }}>{stat.value}</div>
          </motion.div>
        ))}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {data.algorithms.map((algo, i) => (
          <motion.div key={algo.name} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} style={{
            padding: '14px', backgroundColor: 'var(--astrovox-bg)', borderRadius: 'var(--astrovox-radius-sm)',
            border: '1px solid var(--astrovox-border)', display: 'flex', alignItems: 'center', gap: '12px'
          }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: statusColor(algo.status), boxShadow: `0 0 8px ${statusColor(algo.status)}` }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--astrovox-text)' }}>{algo.name}</div>
              <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>{algo.description} · {algo.qubits} qubits</div>
            </div>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase' }}>Fidelity</div>
                <div style={{ fontSize: '12px', fontWeight: '600', color: algo.fidelity > 95 ? '#34d399' : '#fbbf24', fontFamily: 'monospace' }}>{algo.fidelity.toFixed(1)}%</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase' }}>Depth</div>
                <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--astrovox-text)', fontFamily: 'monospace' }}>{algo.circuitDepth}</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase' }}>Speedup</div>
                <div style={{ fontSize: '11px', fontWeight: '600', color: '#a78bfa' }}>{algo.speedup}</div>
              </div>
              <span style={{
                padding: '2px 8px', borderRadius: '4px', fontSize: '9px', textTransform: 'uppercase',
                backgroundColor: `${statusColor(algo.status)}22`, color: statusColor(algo.status), border: `1px solid ${statusColor(algo.status)}44`
              }}>{algo.status}</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
