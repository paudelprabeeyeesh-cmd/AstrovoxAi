import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function UsageDashboard({ usage, conversations, users }) {
  const [timeRange, setTimeRange] = useState('7d')
  const [selectedUser, setSelectedUser] = useState('all')

  const filteredConversations = selectedUser === 'all' ? conversations : conversations?.filter(c => c.userId === selectedUser) || []
  const totalMessages = filteredConversations?.reduce((sum, c) => sum + (c.messageCount || 0), 0) || 0
  const avgMessagesPerUser = users?.length ? Math.round(totalMessages / users.length) : 0

  const usageByHour = useMemo(() => {
    return Array.from({ length: 24 }, (_, i) => ({
      hour: `${i.toString().padStart(2, '0')}:00`,
      count: Math.floor(Math.random() * 100) + 10
    }))
  }, [])

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="activity" size={22} style={{ color: 'var(--astrovox-accent)' }} />
            Usage Dashboard
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Platform usage statistics and trends
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit' }}
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
          <select
            value={selectedUser}
            onChange={(e) => setSelectedUser(e.target.value)}
            style={{ padding: '6px 12px', backgroundColor: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)', color: 'var(--astrovox-text)', fontSize: '12px', fontFamily: 'inherit' }}
          >
            <option value="all">All Users</option>
            {users?.map(u => <option key={u.id} value={u.id}>{u.name || u.email}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px' }}>
        {[
          { label: 'Total Conversations', value: filteredConversations?.length?.toLocaleString() || '0', icon: 'chat' },
          { label: 'Total Messages', value: totalMessages.toLocaleString(), icon: 'message' },
          { label: 'Avg Messages/User', value: avgMessagesPerUser.toString(), icon: 'user' },
          { label: 'Peak Usage', value: '2.4K', icon: 'zap' }
        ].map(stat => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
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
            <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--astrovox-text)' }}>{stat.value}</div>
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
        <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: '600' }}>Usage by Hour</h3>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '150px' }}>
          {usageByHour.map((d, i) => (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: `${(d.count / Math.max(...usageByHour.map(x => x.count))) * 100}%` }}
                transition={{ duration: 0.4, delay: i * 0.02 }}
                style={{
                  width: '100%',
                  backgroundColor: 'var(--astrovox-accent)',
                  borderRadius: '2px 2px 0 0',
                  minHeight: '2px'
                }}
              />
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '8px' }}>
          <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)' }}>00:00</span>
          <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)' }}>12:00</span>
          <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)' }}>23:00</span>
        </div>
      </div>
    </div>
  )
}
