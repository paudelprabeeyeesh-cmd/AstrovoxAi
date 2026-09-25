import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function CostDashboard({ costs, timeRange = '30d' }) {
  const [modelFilter, setModelFilter] = useState('all')
  const [view, setView] = useState('daily')

  const filteredCosts = modelFilter === 'all' ? costs : costs?.filter(c => c.model === modelFilter) || []
  const models = [...new Set(costs?.map(c => c.model) || [])]

  const totalCost = filteredCosts.reduce((sum, c) => sum + (c.cost || 0), 0)
  const totalTokens = filteredCosts.reduce((sum, c) => sum + (c.tokens || 0), 0)

  const dailyData = useMemo(() => {
    const days = parseInt(timeRange)
    return Array.from({ length: days }, (_, i) => {
      const date = new Date(Date.now() - (days - 1 - i) * 86400000)
      const dayCosts = filteredCosts.filter(c => new Date(c.date).toDateString() === date.toDateString())
      return {
        date: date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
        cost: dayCosts.reduce((sum, c) => sum + (c.cost || 0), 0),
        tokens: dayCosts.reduce((sum, c) => sum + (c.tokens || 0), 0)
      }
    })
  }, [filteredCosts, timeRange])

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="zap" size={22} style={{ color: 'var(--astrovox-warning)' }} />
            Cost Dashboard
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Monitor API usage and associated costs
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={modelFilter}
            onChange={(e) => setModelFilter(e.target.value)}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit' }}
          >
            <option value="all">All Models</option>
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
        {[
          { label: 'Total Cost', value: `$${totalCost.toFixed(2)}`, icon: 'zap' },
          { label: 'Total Tokens', value: totalTokens.toLocaleString(), icon: 'activity' },
          { label: 'Avg Cost/Message', value: `$${filteredCosts.length ? (totalCost / filteredCosts.length).toFixed(4) : '0.00'}`, icon: 'chat' },
          { label: 'Forecast', value: `$${(totalCost * 1.1).toFixed(2)}`, icon: 'activity' }
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
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Icon name={stat.icon} size={16} style={{ color: 'var(--astrovox-primary)' }} />
              <span style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                {stat.label}
              </span>
            </div>
            <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--astrovox-text)' }}>{stat.value}</div>
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
          <h3 style={{ margin: 0, fontSize: '14px', fontWeight: '600' }}>Daily Cost</h3>
          <div style={{ display: 'flex', gap: '4px' }}>
            {['daily', 'weekly', 'monthly'].map(v => (
              <button
                key={v}
                onClick={() => setView(v)}
                style={{
                  padding: '4px 10px',
                  backgroundColor: view === v ? 'var(--astrovox-primary)' : 'var(--astrovox-surface-hover)',
                  color: view === v ? 'var(--astrovox-bg)' : 'var(--astrovox-text-muted)',
                  border: `1px solid ${view === v ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`,
                  borderRadius: 'var(--astrovox-radius-sm)',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontFamily: 'inherit',
                  textTransform: 'capitalize'
                }}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px', height: '180px' }}>
          {dailyData.map((d, i) => (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: `${Math.max((d.cost / Math.max(...dailyData.map(x => x.cost), 1)) * 100, 2)}%` }}
                transition={{ duration: 0.4, delay: i * 0.02 }}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--astrovox-warning)',
                  borderRadius: '3px 3px 0 0',
                  minHeight: '3px'
                }}
              />
              <span style={{ fontSize: '8px', color: 'var(--astrovox-text-muted)', writingMode: 'vertical-rl' }}>{d.date.split(' ')[0]}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
