import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function InternalAdmin({ users, conversations, metrics, onUserAction, onSystemAction }) {
  const [activeTab, setActiveTab] = useState('users')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredUsers = users?.filter(u =>
    u.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.name?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  const tabs = [
    { id: 'users', label: 'Users', icon: 'user' },
    { id: 'conversations', label: 'Conversations', icon: 'chat' },
    { id: 'system', label: 'System', icon: 'settings' },
    { id: 'logs', label: 'Logs', icon: 'activity' }
  ]

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="shield" size={22} style={{ color: 'var(--astrovox-warning)' }} />
            Internal Admin Panel
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            System administration and user management
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => onSystemAction?.('export')}
            style={{ ...buttonStyle }}
          >
            <Icon name="download" size={14} style={{ marginRight: '4px' }} />
            Export
          </button>
          <button
            onClick={() => onSystemAction?.('restart')}
            style={{ ...buttonStyle, borderColor: 'var(--astrovox-warning)', color: 'var(--astrovox-warning)' }}
          >
            <Icon name="refresh" size={14} style={{ marginRight: '4px' }} />
            Restart
          </button>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          gap: '4px',
          padding: '4px',
          backgroundColor: 'var(--astrovox-surface)',
          borderRadius: 'var(--astrovox-radius-lg)',
          border: '1px solid var(--astrovox-border)'
        }}
        role="tablist"
      >
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
            style={{
              flex: 1,
              padding: '8px 12px',
              backgroundColor: activeTab === tab.id ? 'var(--astrovox-surface-hover)' : 'transparent',
              border: 'none',
              borderRadius: 'var(--astrovox-radius-md)',
              color: activeTab === tab.id ? 'var(--astrovox-text)' : 'var(--astrovox-text-muted)',
              cursor: 'pointer',
              fontSize: '12px',
              fontFamily: 'inherit',
              fontWeight: activeTab === tab.id ? '600' : '400',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <Icon name={tab.icon} size={14} />
            {tab.label}
          </button>
        ))}
      </div>

      <div
        style={{
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)',
          overflow: 'hidden'
        }}
      >
        {activeTab === 'users' && (
          <div>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--astrovox-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--astrovox-text)' }}>
                User Management ({filteredUsers.length})
              </span>
              <input
                type="search"
                placeholder="Search users..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: '6px 12px',
                  backgroundColor: 'var(--astrovox-bg)',
                  border: '1px solid var(--astrovox-border)',
                  borderRadius: 'var(--astrovox-radius-md)',
                  color: 'var(--astrovox-text)',
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  width: '200px'
                }}
              />
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--astrovox-border)' }}>
                    {['User', 'Email', 'Role', 'Status', 'Joined', 'Actions'].map(h => (
                      <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: '600' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map(user => (
                    <tr key={user.id} style={{ borderBottom: '1px solid var(--astrovox-border)' }}>
                      <td style={{ padding: '10px 16px', fontSize: '12px', color: 'var(--astrovox-text)' }}>{user.name}</td>
                      <td style={{ padding: '10px 16px', fontSize: '12px', color: 'var(--astrovox-text-muted)' }}>{user.email}</td>
                      <td style={{ padding: '10px 16px', fontSize: '12px' }}>
                        <span style={{
                          padding: '2px 8px',
                          borderRadius: 'var(--astrovox-radius-sm)',
                          backgroundColor: user.role === 'admin' ? 'rgba(6, 182, 212, 0.15)' : 'var(--astrovox-surface)',
                          color: user.role === 'admin' ? 'var(--astrovox-primary)' : 'var(--astrovox-text-muted)',
                          border: `1px solid ${user.role === 'admin' ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`
                        }}>
                          {user.role}
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px', fontSize: '12px' }}>
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          color: user.status === 'active' ? 'var(--astrovox-success)' : 'var(--astrovox-error)'
                        }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor' }} />
                          {user.status}
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px', fontSize: '12px', color: 'var(--astrovox-text-muted)' }}>
                        {new Date(user.createdAt).toLocaleDateString()}
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <button
                          onClick={() => onUserAction?.(user.id, 'suspend')}
                          style={{ ...buttonStyle, fontSize: '10px', padding: '4px 8px' }}
                        >
                          Suspend
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'conversations' && (
          <div style={{ padding: '24px', textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '12px' }}>
            <Icon name="chat" size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
            <div>Conversation management interface</div>
            <div style={{ marginTop: '4px', fontSize: '11px' }}>
              View, moderate, and manage all platform conversations
            </div>
          </div>
        )}

        {activeTab === 'system' && (
          <div style={{ padding: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              {[
                { label: 'CPU Usage', value: '45%', status: 'healthy' },
                { label: 'Memory', value: '2.1GB / 4GB', status: 'healthy' },
                { label: 'Disk', value: '120GB / 500GB', status: 'healthy' },
                { label: 'Network', value: '1.2 Gbps', status: 'healthy' }
              ].map(stat => (
                <div key={stat.label} style={{ padding: '12px', backgroundColor: 'var(--astrovox-surface-hover)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginBottom: '4px' }}>{stat.label}</div>
                  <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)' }}>{stat.value}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'logs' && (
          <div style={{ padding: '16px' }}>
            <div style={{ fontFamily: 'var(--astrovox-font-mono)', fontSize: '11px', color: 'var(--astrovox-text-muted)', backgroundColor: 'var(--astrovox-code)', padding: '12px', borderRadius: 'var(--astrovox-radius-md)', maxHeight: '300px', overflowY: 'auto' }}>
              {[`[${new Date().toISOString()}] INFO: System initialized`, `[${new Date().toISOString()}] INFO: User authentication service ready`, `[${new Date().toISOString()}] WARN: High memory usage detected on node-3`, `[${new Date().toISOString()}] INFO: Scheduled maintenance completed`].map((log, i) => (
                <div key={i} style={{ marginBottom: '4px' }}>{log}</div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const buttonStyle = {
  padding: '6px 14px',
  backgroundColor: 'var(--astrovox-surface-hover)',
  color: 'var(--astrovox-text)',
  border: '1px solid var(--astrovox-border)',
  borderRadius: 'var(--astrovox-radius-md)',
  cursor: 'pointer',
  fontSize: '12px',
  fontFamily: 'inherit',
  display: 'flex',
  alignItems: 'center'
}
