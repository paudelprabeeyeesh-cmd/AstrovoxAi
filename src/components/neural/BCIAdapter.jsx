import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { bciConnect, bciDisconnect, bciDevices } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

export function BCIAdapter({ className = '', style = {} }) {
  const [deviceId, setDeviceId] = useState('stub_device')
  const [deviceType, setDeviceType] = useState('eeg')
  const [sampleRate, setSampleRate] = useState(250)
  const [connected, setConnected] = useState(false)
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    bciDevices().then((res) => {
      setDevices(res.devices || [])
    }).catch(() => {})
  }, [])

  const connect = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await bciConnect(deviceId, deviceType, sampleRate)
      setConnected(true)
      setDevices((prev) => [...prev, res.connection])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [deviceId, deviceType, sampleRate])

  const disconnect = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await bciDisconnect(deviceId)
      setConnected(false)
      setDevices((prev) => prev.filter((d) => d.device_id !== deviceId))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [deviceId])

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: NEURAL_COLORS.cardBackground,
        border: `1px solid ${NEURAL_COLORS.border}`,
        borderRadius: '16px',
        padding: '24px',
        backdropFilter: 'blur(12px)',
        ...style,
      }}
    >
      <h3 style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.accent, fontSize: '18px', fontWeight: 600 }}>
        Brain-Computer Interface Adapter
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Connect and manage BCI devices (EEG, EMG, MEG).
      </p>

      <div style={{ marginBottom: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <input
          value={deviceId}
          onChange={(e) => setDeviceId(e.target.value)}
          placeholder="Device ID"
          style={{
            flex: 1,
            minWidth: '120px',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        />
        <select
          value={deviceType}
          onChange={(e) => setDeviceType(e.target.value)}
          style={{
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        >
          <option value="eeg">EEG</option>
          <option value="emg">EMG</option>
          <option value="meg">MEG</option>
        </select>
        <input
          type="number"
          value={sampleRate}
          onChange={(e) => setSampleRate(parseInt(e.target.value || '250', 10))}
          style={{
            width: '80px',
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        />
      </div>

      <div style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
        <button
          onClick={connect}
          disabled={loading || connected}
          style={{
            background: `linear-gradient(135deg, ${NEURAL_COLORS.primary}40, ${NEURAL_COLORS.primary}20)`,
            border: `1px solid ${NEURAL_COLORS.primary}60`,
            borderRadius: '8px',
            padding: '8px 16px',
            color: NEURAL_COLORS.accent,
            fontSize: '13px',
            fontWeight: 500,
            cursor: loading || connected ? 'not-allowed' : 'pointer',
            opacity: loading || connected ? 0.6 : 1,
          }}
        >
          {connected ? 'Connected' : 'Connect'}
        </button>
        <button
          onClick={disconnect}
          disabled={loading || !connected}
          style={{
            background: `linear-gradient(135deg, #ef444440, #ef444420)`,
            border: `1px solid #ef444460`,
            borderRadius: '8px',
            padding: '8px 16px',
            color: '#f87171',
            fontSize: '13px',
            fontWeight: 500,
            cursor: loading || !connected ? 'not-allowed' : 'pointer',
            opacity: loading || !connected ? 0.6 : 1,
          }}
        >
          Disconnect
        </button>
      </div>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      <div>
        <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '8px' }}>
          Connected Devices ({devices.length})
        </div>
        {devices.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {devices.map((d) => (
              <div
                key={d.device_id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  background: 'rgba(0,0,0,0.2)',
                  border: `1px solid ${NEURAL_COLORS.border}`,
                  borderRadius: '6px',
                  padding: '8px 12px',
                }}
              >
                <div>
                  <div style={{ color: NEURAL_COLORS.text, fontSize: '12px', fontWeight: 600 }}>{d.device_id}</div>
                  <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px' }}>
                    {d.device_type?.toUpperCase()} @ {d.sample_rate_hz}Hz | {d.channels?.length || 0} channels
                  </div>
                </div>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: d.status === 'connected' ? '#10b981' : '#ef4444',
                }} />
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: NEURAL_COLORS.muted, fontSize: '12px' }}>No devices connected.</div>
        )}
      </div>
    </motion.div>
  )
}
