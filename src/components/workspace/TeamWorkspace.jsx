import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function TeamWorkspace({ team, members, onInvite, onLeave }) {
  const [isInviting, setIsInviting] = useState(false)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('member')

  const handleInvite = useCallback(() => {
    if (email.trim()) {
      onInvite?.({ email: email.trim(), role, invitedAt: new Date().toISOString() })
      setEmail('')
      setIsInviting(false)
    }
  }, [email, role, onInvite])

  const roleColors = {
    owner: 'var(--astrovox-warning)',
    admin: 'var(--astrovox-primary)',
    member: 'var(--astrovox-success)',
    viewer: 'var(--astrovox-text-muted)'
  }

  return (
    <div
      style={{
        padding: '16px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Icon name="team" size={22} style={{ color: 'var(--astrovox-primary)' }} />
          <div>
            <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--astrovox-text)' }}>
              {team?.name || 'Team Workspace'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
              {members?.length || 0} members
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setIsInviting(!isInviting)}
            style={{
              padding: '6px 14px',
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
            Invite
          </button>
          {onLeave && (
            <button
              onClick={onLeave}
              style={{
                padding: '6px 14px',
                backgroundColor: 'transparent',
                color: 'var(--astrovox-error)',
                border: '1px solid var(--astrovox-error)',
                borderRadius: 'var(--astrovox-radius-md)',
                cursor: 'pointer',
                fontSize: '12px',
                fontFamily: 'inherit'
              }}
            >
              Leave
            </button>
          )}
        </div>
      </div>

      <AnimatePresence>
        {isInviting && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ marginBottom: '16px' }}
          >
            <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="colleague@example.com"
                onKeyDown={(e) => { if (e.key === 'Enter') handleInvite() }}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  backgroundColor: 'var(--astrovox-bg)',
                  border: '1px solid var(--astrovox-border)',
                  borderRadius: 'var(--astrovox-radius-md)',
                  color: 'var(--astrovox-text)',
                  fontSize: '12px',
                  fontFamily: 'inherit',
                  outline: 'none'
                }}
              />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                style={{
                  padding: '8px 12px',
                  backgroundColor: 'var(--astrovox-bg)',
                  border: '1px solid var(--astrovox-border)',
                  borderRadius: 'var(--astrovox-radius-md)',
                  color: 'var(--astrovox-text)',
                  fontSize: '12px',
                  fontFamily: 'inherit'
                }}
              >
                <option value="member">Member</option>
                <option value="admin">Admin</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => { setIsInviting(false); setEmail('') }}
                style={{ ...buttonStyle }}
              >
                Cancel
              </button>
              <button onClick={handleInvite} style={{ ...buttonStyle, backgroundColor: 'var(--astrovox-primary)', color: 'var(--astrovox-bg)' }}>
                Send Invite
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {members?.map((member, index) => (
          <motion.div
            key={member.id}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '8px 12px',
              backgroundColor: 'var(--astrovox-surface-hover)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-md)'
            }}
          >
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: 'var(--astrovox-primary)',
                color: 'var(--astrovox-bg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '11px',
                fontWeight: '600',
                flexShrink: 0
              }}
            >
              {member.name?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '12px', fontWeight: '500', color: 'var(--astrovox-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {member.name || member.email}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>
                {member.email}
              </div>
            </div>
            <span
              style={{
                fontSize: '10px',
                padding: '2px 8px',
                backgroundColor: 'var(--astrovox-surface)',
                color: roleColors[member.role] || roleColors.member,
                borderRadius: 'var(--astrovox-radius-sm)',
                textTransform: 'uppercase',
                fontWeight: '600',
                border: `1px solid ${roleColors[member.role] || roleColors.member}`
              }}
            >
              {member.role}
            </span>
          </motion.div>
        ))}
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
  fontFamily: 'inherit'
}
