import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function ModelPerformanceDashboard({ models, onUpdateModel }) {
  const [selectedModel, setSelectedModel] = useState(models?.[0]?.id || '')
  const [timeRange, setTimeRange] = useState('7d')

  const model = models?.find(m => m.id === selectedModel) || models?.[0]

  const metrics = useMemo(() => {
    if (!model) return []
    return [
      { label: 'Latency (p50)', value: `${model.latencyP50 || 0}ms`, change: '-5.2%', up: true },
      { label: 'Latency (p99)', value: `${model.latencyP99 || 0}ms`, change: '-2.1%', up: true },
      { label: 'Throughput', value: `${(model.throughput || 0).toFixed(1)} req/s`, change: '+12.3%', up: true },
      { label: 'Error Rate', value: `${((model.errorRate || 0) * 100).toFixed(2)}%`, change: '-0.5%', up: true },
      { label: 'Avg Tokens', value: model.avgTokens?.toLocaleString() || '0', change: '+3.1%', up: false },
      { label: 'Cost per 1K', value: `$${model.costPer1K?.toFixed(4) || '0.00'}`, change: '-1.2%', up: true }
    ]
  }, [model])

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="activity" size={22} style={{ color: 'var(--astrovox-secondary)' }} />
            Model Performance
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Real-time LLM performance metrics
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit' }}
          >
            {models?.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit' }}
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
        </div>
      </div>

      {model && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', backgroundColor: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-lg)' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                backgroundColor: 'var(--astrovox-primary)',
                color: 'var(--astrovox-bg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                fontWeight: '700'
              }}
            >
              {model.name?.charAt(0) || 'M'}
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>{model.name}</div>
              <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
                {model.provider} • {model.status === 'active' ? 'Active' : 'Inactive'}
              </div>
            </div>
            <div style={{ marginLeft: 'auto' }}>
              <span
                style={{
                  padding: '4px 10px',
                  borderRadius: 'var(--astrovox-radius-sm)',
                  fontSize: '10px',
                  fontWeight: '600',
                  backgroundColor: model.status === 'active' ? 'rgba(52, 211, 153, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                  color: model.status === 'active' ? 'var(--astrovox-success)' : 'var(--astrovox-text-muted)',
                  border: `1px solid ${model.status === 'active' ? 'var(--astrovox-success)' : 'var(--astrovox-border)'}`,
                  textTransform: 'uppercase'
                }}
              >
                {model.status}
              </span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
            {metrics.map((metric, index) => (
              <motion.div
                key={metric.label}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                style={{
                  padding: '14px',
                  backgroundColor: 'var(--astrovox-surface)',
                  border: '1px solid var(--astrovox-border)',
                  borderRadius: 'var(--astrovox-radius-lg)'
                }}
              >
                <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  {metric.label}
                </div>
                <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--astrovox-text)', marginBottom: '4px' }}>
                  {metric.value}
                </div>
                <div style={{ fontSize: '11px', color: metric.up ? 'var(--astrovox-success)' : 'var(--astrovox-error)', fontWeight: '600' }}>
                  {metric.change}
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
            <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: '600' }}>Latency Distribution</h3>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '120px' }}>
              {Array.from({ length: 20 }, (_, i) => ({
                latency: Math.floor(Math.random() * 500) + 100,
                count: Math.floor(Math.random() * 50) + 10
              })).map((bar, i) => (
                <motion.div
                  key={i}
                  initial={{ height: 0 }}
                  animate={{ height: `${(bar.count / 60) * 100}%` }}
                  transition={{ duration: 0.3, delay: i * 0.02 }}
                  style={{
                    flex: 1,
                    backgroundColor: 'var(--astrovox-secondary)',
                    borderRadius: '2px 2px 0 0',
                    minHeight: '3px'
                  }}
                />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
