import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getMonitorHealth, getMonitorAlerts, recordMonitorEvent } from '../../services/monitoringService'

export default function OmnipresentMonitoring() {
  const [health, setHealth] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [isMonitoring, setIsMonitoring] = useState(true)

  useEffect(() => {
    if (!isMonitoring) return
    const loadData = async () => {
      try {
        const healthData = await getMonitorHealth()
        setHealth(healthData)
        const alertsData = await getMonitorAlerts()
        setAlerts(alertsData.alerts || [])
      } catch (e) {
        console.error('Monitoring failed:', e)
      }
    }
    loadData()
    const interval = setInterval(loadData, 5000)
    return () => clearInterval(interval)
  }, [isMonitoring])

  if (!health) return null

  return (
    <div style={{
      backgroundColor: 'rgba(4,8,20,0.6)',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      padding: '16px'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{
          margin: 0,
          fontSize: '13px',
          color: '#f59e0b',
          textTransform: 'uppercase',
          letterSpacing: '1px'
        }}>
          👁️ Omnipresent Monitoring
        </h3>
        <button
          onClick={() => setIsMonitoring(!isMonitoring)}
          style={{
            background: isMonitoring ? '#22c55e' : '#ef4444',
            border: 'none',
            borderRadius: '4px',
            color: '#02040a',
            padding: '4px 8px',
            fontSize: '10px',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          {isMonitoring ? 'LIVE' : 'PAUSED'}
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '8px',
        marginBottom: '12px'
      }}>
        {[
          { label: 'Monitors', value: health.monitors || 0, color: '#06b6d4' },
          { label: 'Events', value: health.events || 0, color: '#22c55e' },
          { label: 'Alerts', value: health.alerts || 0, color: health.alerts > 0 ? '#ef4444' : '#22c55e' },
        ].map((stat, idx) => (
          <div key={idx} style={{
            padding: '8px',
            backgroundColor: 'rgba(6,182,212,0.05)',
            borderRadius: '6px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase' }}>{stat.label}</div>
            <div style={{ fontSize: '18px', color: stat.color, fontWeight: 700, fontFamily: 'monospace' }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {alerts.length > 0 && (
        <div>
          <div style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '8px' }}>
            Active Alerts
          </div>
          <AnimatePresence>
            {alerts.slice(0, 5).map((alert, idx) => (
              <motion.div
                key={alert.event_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                style={{
                  padding: '6px 8px',
                  backgroundColor: alert.severity === 'critical' ? 'rgba(239,68,68,0.1)' : 'rgba(245,158,11,0.1)',
                  border: `1px solid ${alert.severity === 'critical' ? '#ef4444' : '#f59e0b'}`,
                  borderRadius: '4px',
                  marginBottom: '4px',
                  fontSize: '10px',
                  color: '#94a3b8',
                  fontFamily: 'monospace'
                }}
              >
                [{alert.severity.toUpperCase()}] {alert.source}: {alert.event_type}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
