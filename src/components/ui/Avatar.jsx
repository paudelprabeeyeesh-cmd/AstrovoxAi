import React from 'react'
import { getInitials, stringToColor, getContrastColor } from '../../utils/avatar'
import Icon from '../../design/Iconography.jsx'

export function Avatar({
  name = '',
  src = null,
  size = 40,
  status = null,
  style = {}
}) {
  const initials = getInitials(name)
  const bgColor = stringToColor(name)
  const textColor = getContrastColor(bgColor)

  const statusColors = {
    online: '#34d399',
    away: '#fbbf24',
    busy: '#ef4444',
    offline: '#64748b'
  }

  return (
    <div
      style={{
        position: 'relative',
        width: size,
        height: size,
        flexShrink: 0,
        ...style
      }}
      title={name}
    >
      {src ? (
        <img
          src={src}
          alt={name}
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            objectFit: 'cover',
            border: '2px solid var(--astrovox-border)'
          }}
        />
      ) : (
        <div style={{
          width: '100%',
          height: '100%',
          borderRadius: '50%',
          backgroundColor: bgColor,
          color: textColor,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: size * 0.4,
          fontWeight: '600',
          border: '2px solid var(--astrovox-border)',
          userSelect: 'none'
        }}>
          {initials}
        </div>
      )}
      {status && (
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            right: 0,
            width: size * 0.3,
            height: size * 0.3,
            borderRadius: '50%',
            backgroundColor: statusColors[status] || statusColors.offline,
            border: '2px solid var(--astrovox-surface)',
            boxSizing: 'border-box'
          }}
        />
      )}
    </div>
  )
}

export function AvatarGroup({ children, max = 4 }) {
  const childArray = React.Children.toArray(children)
  const visible = childArray.slice(0, max)
  const remaining = childArray.length - max

  return (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      {visible.map((child, i) => {
        const childSize = (child.props?.size || 40) + 8
        return React.cloneElement(child, {
          style: {
            ...child.props?.style,
            marginLeft: i > 0 ? -childSize / 3 : 0,
            border: '2px solid var(--astrovox-surface)'
          }
        })
      })}
      {remaining > 0 && (
        <div
          style={{
            width: (childArray[0]?.props?.size || 40) + 8,
            height: (childArray[0]?.props?.size || 40) + 8,
            borderRadius: '50%',
            backgroundColor: 'var(--astrovox-surface-hover)',
            border: '2px solid var(--astrovox-surface)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '11px',
            fontWeight: '600',
            color: 'var(--astrovox-text-muted)',
            marginLeft: -((childArray[0]?.props?.size || 40) / 3)
          }}
        >
          +{remaining}
        </div>
      )}
    </div>
  )
}
