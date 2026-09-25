import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function CustomerAdmin({ organization, members, usage, billing, onUpdatePlan, onManageMembers }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [isUpgrading, setIsUpgrading] = useState(false)

  const tabs = [
    { id: 'overview', label: 'Overview', icon: 'activity' },
    { id: 'members', label: 'Members', icon: 'team' },
    { id: 'billing', label: 'Billing', icon: 'zap' },
    { id: 'settings', label: 'Settings', icon: 'settings' }
  ]

  const usagePercentage = usage ? Math.min((usage.current / usage.limit) * 100, 100) : 0

  return (
    <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="settings" size={22} style={{ color: 'var(--astrovox-secondary)' }} />
            {organization?.name || 'Organization Admin'}
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
            Plan: {organization?.plan || 'Free'} • {members?.length || 0} seats
          </p>
        </div>
        <button
          onClick={() => setIsUpgrading(!isUpgrading)}
          style={{
            padding: '8px 16px',
            backgroundColor: 'var(--astrovox-primary)',
            color: 'var(--astrovox-bg)',
            border: 'none',
            borderRadius: 'var(--astrovox-radius-md)',
            cursor: 'pointer',
            fontSize: '12px',
            fontFamily: 'inherit',
            fontWeight: '600'
          }}
        >
          {isUpgrading ? 'Cancel' : 'Upgrade Plan'}
        </button>
      </div>

      {isUpgrading && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            padding: '16px',
            backgroundColor: 'var(--astrovox-surface)',
            border: '1px solid var(--astrovox-primary)',
            borderRadius: 'var(--astrovox-radius-lg)'
          }}
        >
          <h3 style={{ margin: '0 0 12px', fontSize: '14px', fontWeight: '600' }}>Available Plans</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
            {['Free', 'Pro', 'Team', 'Enterprise'].map(plan => (
              <div
                key={plan}
                style={{
                  padding: '16px',
                  backgroundColor: 'var(--astrovox-surface-hover)',
                  border: organization?.plan === plan ? '2px solid var(--astrovox-primary)' : '1px solid var(--astrovox-border)',
                  borderRadius: 'var(--astrovox-radius-md)',
                  textAlign: 'center'
                }}
              >
                <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--astrovox-text)', marginBottom: '4px' }}>{plan}</div>
                <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--astrovox-primary)', marginBottom: '8px' }}>
                  {plan === 'Free' ? '$0' : plan === 'Pro' ? '$20' : plan === 'Team' ? '$50' : 'Custom'}
                </div>
                <button
                  onClick={() => { onUpdatePlan?.(plan); setIsUpgrading(false) }}
                  style={{
                    width: '100%',
                    padding: '8px',
                    backgroundColor: organization?.plan === plan ? 'var(--astrovox-primary)' : 'transparent',
                    color: organization?.plan === plan ? 'var(--astrovox-bg)' : 'var(--astrovox-text)',
                    border: organization?.plan === plan ? 'none' : '1px solid var(--astrovox-border)',
                    borderRadius: 'var(--astrovox-radius-md)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontFamily: 'inherit'
                  }}
                >
                  {organization?.plan === plan ? 'Current' : 'Select'}
                </button>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <div
        style={{
          display: 'flex',
          gap: '4px',
          padding: '4px',
          backgroundColor: 'var(--astrovox-surface)',
          borderRadius: 'var(--astrovox-radius-lg)',
          border: '1px solid var(--astrovox-border)'
        }}
      >
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
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
          padding: '16px'
        }}
      >
        {activeTab === 'overview' && (
          <div>
            <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>Usage Overview</h3>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', color: 'var(--astrovox-text-muted)' }}>Messages this month</span>
                <span style={{ fontSize: '12px', color: 'var(--astrovox-text)', fontWeight: '600' }}>
                  {usage?.current?.toLocaleString() || 0} / {usage?.limit?.toLocaleString() || 0}
                </span>
              </div>
              <div style={{ height: '8px', backgroundColor: 'var(--astrovox-border)', borderRadius: '4px', overflow: 'hidden' }}>
                <motion.div
                  animate={{ width: `${usagePercentage}%` }}
                  transition={{ duration: 0.5 }}
                  style={{
                    height: '100%',
                    backgroundColor: usagePercentage > 80 ? 'var(--astrovox-error)' : 'var(--astrovox-primary)',
                    borderRadius: '4px'
                  }}
                />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px' }}>
              {[
                { label: 'Total Messages', value: usage?.current?.toLocaleString() || '0' },
                { label: 'Tokens Used', value: usage?.tokens?.toLocaleString() || '0' },
                { label: 'Active Users', value: members?.length || '0' },
                { label: 'API Calls', value: usage?.apiCalls?.toLocaleString() || '0' }
              ].map(stat => (
                <div key={stat.label} style={{ padding: '12px', backgroundColor: 'var(--astrovox-surface-hover)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius-md)' }}>
                  <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginBottom: '4px' }}>{stat.label}</div>
                  <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--astrovox-text)' }}>{stat.value}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'members' && (
          <div>
            <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>Team Members</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {members?.map((member, index) => (
                <motion.div
                  key={member.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 12px',
                    backgroundColor: 'var(--astrovox-surface-hover)',
                    border: '1px solid var(--astrovox-border)',
                    borderRadius: 'var(--astrovox-radius-md)'
                  }}
                >
                  <div style={{ flex: 1, fontSize: '12px', color: 'var(--astrovox-text)' }}>{member.name || member.email}</div>
                  <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>{member.role}</span>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'billing' && (
          <div>
            <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>Billing Information</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {billing && Object.entries(billing).map(([key, value]) => (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--astrovox-border)' }}>
                  <span style={{ fontSize: '12px', color: 'var(--astrovox-text-muted)', textTransform: 'capitalize' }}>{key}</span>
                  <span style={{ fontSize: '12px', color: 'var(--astrovox-text)', fontWeight: '600' }}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div>
            <h3 style={{ margin: '0 0 16px', fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>Organization Settings</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {['Allow public sharing', 'Enable audit logs', 'Require 2FA', 'Data retention (days)'].map(setting => (
                <div key={setting} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0' }}>
                  <span style={{ fontSize: '12px', color: 'var(--astrovox-text)' }}>{setting}</span>
                  <input
                    type="checkbox"
                    style={{ width: '18px', height: '18px', accentColor: 'var(--astrovox-primary)' }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
