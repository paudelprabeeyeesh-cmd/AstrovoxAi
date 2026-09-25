import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function AnalyticsDashboard({ data, timeRange = '7d' }) {
  const [metric, setMetric] = useState('messages')
  const [view, setView] = useState('chart')

  const chartData = useMemo(() => {
    const days = parseInt(timeRange)
    return Array.from({ length: days }, (_, i) => ({
      date: new Date(Date.now() - (days - 1 - i) * 86400000).toLocaleDateString('en-US', { weekday: 'short' }),
      value: Math.floor(Math.random() * 1000) + 500
    }))
  }, [timeRange])

  const maxValue = Math.max(...chartData.map(d => d.value))

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="activity" size={22} style={{ color: 'var(--astrovox-primary)' }} />
            Analytics Dashboard
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Track engagement and performance metrics
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={timeRange}
            onChange={(e) => {}}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit' }}
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
        {[
          { label: 'Total Messages', value: '24.5K', change: '+12.5%', up: true },
          { label: 'Active Users', value: '1,234', change: '+5.2%', up: true },
          { label: 'Avg Response Time', value: '1.2s', change: '-8.1%', up: true },
          { label: 'Satisfaction', value: '94%', change: '+2.3%', up: true }
        ].map(stat => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: '16px',
              backgroundColor: 'var(--astrovox-surface)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-lg)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {stat.label}
            </div>
            <div style={{ fontSize: '24px', fontWeight: '700', color: 'var(--astrovox-text)', marginBottom: '4px' }}>
              {stat.value}
            </div>
            <div style={{ fontSize: '11px', color: stat.up ? 'var(--astrovox-success)' : 'var(--astrovox-error)', fontWeight: '600' }}>
              {stat.change} vs last period
            </div>
          </motion.div>
        ))}
      </div>

      <div
        style={{
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)',
          padding: '16px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>Message Volume</h3>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['messages', 'users', 'tokens'].map(m => (
              <button
                key={m}
                onClick={() => setMetric(m)}
                style={{
                  padding: '4px 10px',
                  backgroundColor: metric === m ? 'var(--astrovox-primary)' : 'var(--astrovox-surface-hover)',
                  color: metric === m ? 'var(--astrovox-bg)' : 'var(--astrovox-text-muted)',
                  border: `1px solid ${metric === m ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`,
                  borderRadius: 'var(--astrovox-radius-sm)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontFamily: 'inherit',
                  textTransform: 'capitalize'
                }}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: '200px', padding: '0 8px' }}>
          {chartData.map((d, i) => (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: `${(d.value / maxValue) * 100}%` }}
                transition={{ duration: 0.5, delay: i * 0.03 }}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--astrovox-primary)',
                  borderRadius: '4px 4px 0 0',
                  minHeight: '4px'
                }}
              />
              <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)' }}>{d.date}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
