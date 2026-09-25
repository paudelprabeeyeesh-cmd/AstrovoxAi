import { useQuantumState } from '../../hooks/holographic/useQuantumState'
import { HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'

export function QuantumStateVisualization({ className = '', style = {} }) {
  const { qubits, isSimulating, coherence, entanglement, measurements, startSimulation, stopSimulation, measure, measureAll, reset, applyGate, createEntanglement } = useQuantumState()

  useEffect(() => {
    if (qubits.length === 0) {
      startSimulation()
    }
  }, [])

  const handleMeasureAll = () => {
    measureAll()
  }

  const handleReset = () => {
    reset()
    startSimulation()
  }

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        ...style
      }}
    >
      <div style={{
        padding: '16px',
        borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h3 style={{
            margin: '0 0 4px 0',
            color: HOLOGRAPHIC_COLORS.accent,
            fontSize: '16px',
            fontWeight: 600
          }}>
            Quantum State Simulator
          </h3>
          <p style={{ margin: 0, color: 'var(--astrovox-text-muted)', fontSize: '12px' }}>
            Qubits: {qubits.length} | Coherence: {(coherence * 100).toFixed(0)}% | Entangled: {entanglement.length}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={isSimulating ? stopSimulation : startSimulation}
            style={{
              padding: '6px 12px',
              background: isSimulating ? 'rgba(239, 68, 68, 0.1)' : 'rgba(52, 211, 153, 0.1)',
              border: `1px solid ${isSimulating ? 'rgba(239, 68, 68, 0.4)' : 'rgba(52, 211, 153, 0.4)'}`,
              borderRadius: '6px',
              color: isSimulating ? HOLOGRAPHIC_COLORS.error : HOLOGRAPHIC_COLORS.success,
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            {isSimulating ? 'Stop' : 'Start'}
          </button>
          <button
            onClick={handleMeasureAll}
            style={{
              padding: '6px 12px',
              background: 'rgba(6, 182, 212, 0.1)',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              borderRadius: '6px',
              color: HOLOGRAPHIC_COLORS.accent,
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            Measure All
          </button>
          <button
            onClick={handleReset}
            style={{
              padding: '6px 12px',
              background: 'rgba(167, 139, 250, 0.1)',
              border: '1px solid rgba(167, 139, 250, 0.4)',
              borderRadius: '6px',
              color: HOLOGRAPHIC_COLORS.quantum,
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            Reset
          </button>
        </div>
      </div>

      <div style={{ padding: '16px' }}>
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '12px',
          justifyContent: 'center',
          marginBottom: '20px'
        }}>
          {qubits.map((qubit, index) => (
            <div
              key={index}
              style={{
                width: '70px',
                height: '70px',
                position: 'relative'
              }}
            >
              <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%' }}>
                <circle
                  cx="50"
                  cy="50"
                  r="40"
                  fill="none"
                  stroke={`rgba(6, 182, 212, ${qubit.amplitude * 0.3})`}
                  strokeWidth="2"
                  strokeDasharray={`${qubit.amplitude * 251} ${251 - qubit.amplitude * 251}`}
                  transform={`rotate(${qubit.phase * (180 / Math.PI)} 50 50)`}
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
              {qubit.entanglement?.length > 0 && (
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
                  {qubit.entanglement.length}
                </div>
              )}
            </div>
          ))}
        </div>

        {entanglement.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ color: HOLOGRAPHIC_COLORS.accent, margin: '0 0 8px 0', fontSize: '13px' }}>
              Entanglements
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {entanglement.map((ent, index) => (
                <div
                  key={ent.id || index}
                  style={{
                    padding: '8px 12px',
                    background: 'rgba(167, 139, 250, 0.1)',
                    borderRadius: '6px',
                    border: `1px solid ${HOLOGRAPHIC_COLORS.quantum}40`,
                    fontSize: '12px'
                  }}
                >
                  <span style={{ color: HOLOGRAPHIC_COLORS.accent }}>
                    q{ent.q1} ↔ q{ent.q2}
                  </span>
                  <span style={{ color: 'var(--astrovox-text-muted)', marginLeft: '8px' }}>
                    {ent.type} | Strength: {(ent.strength * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {measurements.length > 0 && (
          <div>
            <h4 style={{ color: HOLOGRAPHIC_COLORS.accent, margin: '0 0 8px 0', fontSize: '13px' }}>
              Recent Measurements
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '120px', overflowY: 'auto' }}>
              {measurements.slice(-10).map((m, index) => (
                <div
                  key={m.id || index}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '4px 8px',
                    background: 'rgba(6, 182, 212, 0.05)',
                    borderRadius: '4px',
                    fontSize: '11px'
                  }}
                >
                  <span style={{ color: 'var(--astrovox-text)' }}>
                    q{m.qubit}: {m.value.toFixed(2)}
                  </span>
                  <span style={{ color: 'var(--astrovox-text-muted)' }}>
                    {(m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : 'now')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
