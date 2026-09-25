import { motion } from 'framer-motion'
import { HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'

export function NeuralVisualization({ data, type = 'brainwave', className = '', style = {} }) {
  const renderBrainwave = () => {
    if (!data || !data.length) return null

    const maxPower = Math.max(...data.map(d => d.power))
    const bands = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {data.map((band, index) => (
          <div key={index} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{
              color: HOLOGRAPHIC_COLORS.accent,
              fontSize: '11px',
              width: '50px',
              textAlign: 'right'
            }}>
              {bands[index] || `Band ${index}`}
            </span>
            <div style={{
              flex: 1,
              height: '20px',
              background: 'rgba(6, 182, 212, 0.1)',
              borderRadius: '4px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(band.power / maxPower) * 100}%` }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                style={{
                  height: '100%',
                  background: `linear-gradient(90deg, ${HOLOGRAPHIC_COLORS.primary}, ${HOLOGRAPHIC_COLORS.accent})`,
                  borderRadius: '4px',
                  boxShadow: `0 0 10px ${HOLOGRAPHIC_COLORS.primary}40`
                }}
              />
            </div>
            <span style={{
              color: 'var(--astrovox-text-muted)',
              fontSize: '11px',
              width: '40px'
            }}>
              {band.power.toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    )
  }

  const renderConnectivity = () => {
    if (!data || !data.length) return null

    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(8, 1fr)',
        gap: '2px',
        padding: '8px',
        background: 'rgba(2, 4, 10, 0.5)',
        borderRadius: '8px'
      }}>
        {data.slice(0, 64).map((row, i) => (
          <div key={i} style={{ display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: '2px' }}>
            {row.slice(0, 64).map((value, j) => (
              <div
                key={j}
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '2px',
                  background: `rgba(6, 182, 212, ${value})`,
                  boxShadow: value > 0.7 ? `0 0 4px ${HOLOGRAPHIC_COLORS.primary}` : 'none'
                }}
              />
            ))}
          </div>
        ))}
      </div>
    )
  }

  const renderThoughtStream = () => {
    if (!data || !data.length) return null

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {data.slice(-10).map((thought, index) => (
          <motion.div
            key={thought.id || index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            style={{
              padding: '8px 12px',
              background: 'rgba(6, 182, 212, 0.1)',
              borderRadius: '6px',
              borderLeft: `3px solid ${HOLOGRAPHIC_COLORS.primary}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <span style={{ color: 'var(--astrovox-text)', fontSize: '12px' }}>
              {thought.content}
            </span>
            <span style={{
              color: HOLOGRAPHIC_COLORS.accent,
              fontSize: '10px',
              opacity: 0.7
            }}>
              {new Date(thought.timestamp).toLocaleTimeString()}
            </span>
          </motion.div>
        ))}
      </div>
    )
  }

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        padding: '20px',
        ...style
      }}
    >
      {type === 'brainwave' && renderBrainwave()}
      {type === 'connectivity' && renderConnectivity()}
      {type === 'thought' && renderThoughtStream()}
    </div>
  )
}

export function QuantumVisualization({ qubits, entanglement, measurements, className = '', style = {} }) {
  const renderQubits = () => {
    if (!qubits || !qubits.length) return null

    return (
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '16px',
        justifyContent: 'center',
        padding: '20px'
      }}>
        {qubits.map((qubit, index) => {
          const angle = qubit.phase * (180 / Math.PI)
          const amplitude = qubit.amplitude
          const entanglementStrength = qubit.entanglement?.length || 0

          return (
            <div
              key={index}
              style={{
                position: 'relative',
                width: '80px',
                height: '80px'
              }}
            >
              <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%' }}>
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke={`rgba(6, 182, 212, ${amplitude * 0.3})`}
                  strokeWidth="2"
                  strokeDasharray={`${amplitude * 251} ${251 - amplitude * 251}`}
                  transform={`rotate(${angle} 50 50)`}
                />
                <circle
                  cx="50"
                  cy="50"
                  r="35"
                  fill="none"
                  stroke={HOLOGRAPHIC_COLORS.quantum}
                  strokeWidth="1"
                  opacity="0.5"
                />
                <text
                  x="50"
                  y="55"
                  textAnchor="middle"
                  fill={HOLOGRAPHIC_COLORS.accent}
                  fontSize="14"
                  fontWeight="bold"
                >
                  {qubit.measured ? qubit.value : 'ψ'}
                </text>
                <text
                  x="50"
                  y="90"
                  textAnchor="middle"
                  fill="var(--astrovox-text-muted)"
                  fontSize="10"
                >
                  q{index}
                </text>
              </svg>
              {entanglementStrength > 0 && (
                <div style={{
                  position: 'absolute',
                  top: '-4px',
                  right: '-4px',
                  width: '16px',
                  height: '16px',
                  borderRadius: '50%',
                  background: HOLOGRAPHIC_COLORS.secondary,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '10px',
                  color: '#fff',
                  fontWeight: 'bold'
                }}>
                  {entanglementStrength}
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  const renderEntanglement = () => {
    if (!entanglement || !entanglement.length) return null

    return (
      <div style={{ padding: '16px' }}>
        <h4 style={{ color: HOLOGRAPHIC_COLORS.accent, margin: '0 0 12px 0', fontSize: '14px' }}>
          Entangled Qubits
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {entanglement.map((ent, index) => (
            <div
              key={ent.id || index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '8px 12px',
                background: 'rgba(167, 139, 250, 0.1)',
                borderRadius: '6px',
                border: `1px solid ${HOLOGRAPHIC_COLORS.quantum}40`
              }}
            >
              <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '12px' }}>
                q{ent.q1} ↔ q{ent.q2}
              </span>
              <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
                {ent.type}
              </span>
              <div style={{
                flex: 1,
                height: '4px',
                background: 'rgba(167, 139, 250, 0.2)',
                borderRadius: '2px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${ent.strength * 100}%`,
                  height: '100%',
                  background: HOLOGRAPHIC_COLORS.quantum,
                  borderRadius: '2px'
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        ...style
      }}
    >
      {renderQubits()}
      {renderEntanglement()}
    </div>
  )
}

export function ConsciousnessMap({ consciousness, focus, meditation, thoughts, className = '', style = {} }) {
  const renderConsciousnessMeter = () => {
    const radius = 40
    const circumference = 2 * Math.PI * radius
    const strokeDasharray = `${consciousness * circumference} ${circumference}`

    return (
      <div style={{ position: 'relative', width: '120px', height: '120px', margin: '0 auto' }}>
        <svg viewBox="0 0 120 120" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke="rgba(6, 182, 212, 0.2)"
            strokeWidth="8"
          />
          <motion.circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={HOLOGRAPHIC_COLORS.consciousness}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={strokeDasharray}
            initial={{ strokeDasharray: `0 ${circumference}` }}
            animate={{ strokeDasharray }}
            transition={{ duration: 1 }}
          />
        </svg>
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '24px', fontWeight: 'bold' }}>
            {(consciousness * 100).toFixed(0)}%
          </span>
          <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '10px' }}>
            Consciousness
          </span>
        </div>
      </div>
    )
  }

  const renderMetrics = () => {
    const metrics = [
      { label: 'Focus', value: focus, color: HOLOGRAPHIC_COLORS.primary },
      { label: 'Meditation', value: meditation, color: HOLOGRAPHIC_COLORS.secondary },
      { label: 'Clarity', value: consciousness, color: HOLOGRAPHIC_COLORS.consciousness }
    ]

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {metrics.map((metric, index) => (
          <div key={index}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '4px'
            }}>
              <span style={{ color: metric.color, fontSize: '12px', fontWeight: 500 }}>
                {metric.label}
              </span>
              <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
                {(metric.value * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{
              height: '6px',
              background: 'rgba(6, 182, 212, 0.1)',
              borderRadius: '3px',
              overflow: 'hidden'
            }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${metric.value * 100}%` }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                style={{
                  height: '100%',
                  background: metric.color,
                  borderRadius: '3px',
                  boxShadow: `0 0 10px ${metric.color}40`
                }}
              />
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        ...style
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        {renderConsciousnessMeter()}
      </div>
      {renderMetrics()}
      {thoughts && thoughts.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <h4 style={{ color: HOLOGRAPHIC_COLORS.accent, margin: '0 0 12px 0', fontSize: '13px' }}>
            Active Thoughts
          </h4>
          <div style={{ maxHeight: '120px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {thoughts.slice(-5).map((thought, index) => (
              <div
                key={index}
                style={{
                  padding: '6px 10px',
                  background: 'rgba(244, 114, 182, 0.1)',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: 'var(--astrovox-text)',
                  borderLeft: `2px solid ${HOLOGRAPHIC_COLORS.consciousness}`
                }}
              >
                {thought.content}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
