function Metric({ label, value, status }) {
  return (
    <div style={{
      border: '1px solid #1e293b',
      borderRadius: '8px',
      padding: '12px',
      backgroundColor: 'rgba(4, 8, 20, 0.55)'
    }}>
      <div style={{ color: '#64748b', fontSize: '10px', letterSpacing: '0.08em' }}>{label}</div>
      <div style={{ color: status === 'offline' ? '#f87171' : '#67e8f9', fontSize: '18px', marginTop: '4px' }}>
        {value}
      </div>
    </div>
  )
}

export default function Telemetry({ totalPackets, dbStatus }) {
  return (
    <section style={{
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '16px',
      backgroundColor: '#02040a'
    }} aria-label="Workspace telemetry">
      <h3 style={{ color: '#67e8f9', fontSize: '12px', letterSpacing: '0.08em', margin: '0 0 12px' }}>
        WORKSPACE STATUS
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
        <Metric label="CONVERSATIONS" value={totalPackets} />
        <Metric label="DATABASE" value={dbStatus.toUpperCase()} status={dbStatus} />
      </div>
    </section>
  )
}
