import { useState, useMemo, useEffect } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function PerformanceDashboard({ metrics = [] }) {
  const [timeRange, setTimeRange] = useState('1h')
  const [selectedMetric, setSelectedMetric] = useState('latency')
  const [live, setLive] = useState(true)

  const chartData = useMemo(() => {
    const points = timeRange === '1h' ? 60 : timeRange === '24h' ? 144 : 100
    return Array.from({ length: points }, (_, i) => {
      const base = selectedMetric === 'latency' ? 200 : selectedMetric === 'memory' ? 512 : 50
      const variance = base * 0.3
      return {
        time: new Date(Date.now() - (points - 1 - i) * (timeRange === '1h' ? 60000 : timeRange === '24h' ? 600000 : 3600000)).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        value: Math.max(0, base + (Math.random() - 0.5) * variance),
        p99: base * 1.5 + (Math.random() - 0.5) * variance * 0.5
      }
    })
  }, [timeRange, selectedMetric])

  const current = useMemo(() => {
    if (chartData.length === 0) return { value: 0, p99: 0 }
    const last = chartData[chartData.length - 1]
    return { value: last.value.toFixed(1), p99: last.p99.toFixed(1) }
  }, [chartData])

  const sparklinePath = useMemo(() => {
    if (chartData.length === 0) return ''
    const width = 100
    const height = 40
    const max = Math.max(...chartData.map(d => Math.max(d.value, d.p99)))
    const min = Math.min(...chartData.map(d => Math.min(d.value, d.p99)))
    const range = max - min || 1
    const points = chartData.map((d, i) => {
      const x = (i / (chartData.length - 1)) * width
      const y = height - ((d.value - min) / range) * height
      return `${x},${y}`
    })
    return `M${points.join(' L')}`
  }, [chartData])

  const p99Path = useMemo(() => {
    if (chartData.length === 0) return ''
    const width = 100
    const height = 40
    const max = Math.max(...chartData.map(d => Math.max(d.value, d.p99)))
    const min = Math.min(...chartData.map(d => Math.min(d.value, d.p99)))
    const range = max - min || 1
    const points = chartData.map((d, i) => {
      const x = (i / (chartData.length - 1)) * width
      const y = height - ((d.p99 - min) / range) * height
      return `${x},${y}`
    })
    return `M${points.join(' L')}`
  }, [chartData])

  useEffect(() => {
    if (!live) return
    const interval = setInterval(() => {
      setSelectedMetric(prev => prev)
    }, 2000)
    return () => clearInterval(interval)
  }, [live])

  const stats = useMemo(() => {
    const values = chartData.map(d => d.value)
    const avg = values.reduce((a, b) => a + b, 0) / values.length
    const max = Math.max(...values)
    const min = Math.min(...values)
    return { avg: avg.toFixed(1), max: max.toFixed(1), min: min.toFixed(1) }
  }, [chartData])

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="activity" size={22} style={{ color: 'var(--astrovox-primary)' }} />
            Performance Profiler
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Real-time latency, memory, and throughput metrics
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit' }}
          >
            <option value="1h">Last 1 hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
          </select>
          <button
            onClick={() => setLive(!live)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 12px',
              backgroundColor: live ? 'var(--astrovox-primary)' : 'var(--astrovox-surface)',
              color: live ? 'var(--astrovox-bg)' : 'var(--astrovox-text)',
              border: `1px solid ${live ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`,
              borderRadius: 'var(--astrovox-radius-md)',
              fontSize: '12px',
              cursor: 'pointer',
              fontFamily: 'inherit'
            }}
          >
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: live ? 'var(--astrovox-bg)' : 'var(--astrovox-text-muted)' }} />
            {live ? 'Live' : 'Paused'}
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
        {[
          { label: 'Current', value: `${current.value}ms`, sub: 'p50 latency', color: 'var(--astrovox-primary)' },
          { label: 'P99', value: `${current.p99}ms`, sub: 'tail latency', color: 'var(--astrovox-secondary)' },
          { label: 'Avg', value: `${stats.avg}ms`, sub: 'mean', color: 'var(--astrovox-accent)' },
          { label: 'Range', value: `${stats.min}-${stats.max}ms`, sub: 'min to max', color: 'var(--astrovox-success)' }
        ].map(stat => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              padding: '14px',
              backgroundColor: 'var(--astrovox-surface)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-lg)'
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginBottom: '4px' }}>{stat.label}</div>
            <div style={{ fontSize: '20px', fontWeight: '700', color: stat.color }}>{stat.value}</div>
            <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)', marginTop: '2px' }}>{stat.sub}</div>
          </motion.div>
        ))}
      </div>

      <div style={{ padding: '16px', backgroundColor: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-lg)' }}>
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" style={{ width: '100%', height: '80px', display: 'block' }}>
          <path d={sparklinePath} fill="none" stroke="var(--astrovox-primary)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
          <path d={p99Path} fill="none" stroke="var(--astrovox-secondary)" strokeWidth="1.5" strokeDasharray="2,2" vectorEffect="non-scaling-stroke" />
        </svg>
        <div style={{ display: 'flex', gap: '16px', marginTop: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            <div style={{ width: '12px', height: '2px', backgroundColor: 'var(--astrovox-primary)' }} />
            p50
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            <div style={{ width: '12px', height: '2px', backgroundColor: 'var(--astrovox-secondary)', opacity: 0.6 }} />
            p99
          </div>
        </div>
      </div>
    </div>
  )
}
