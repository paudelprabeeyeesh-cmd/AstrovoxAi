import React from 'react'

export function Skeleton({ width = '100%', height = '16px', borderRadius = '4px', style = {} }) {
  return (
    <div
      style={{
        width,
        height,
        borderRadius,
        backgroundColor: 'var(--astrovox-surface-hover)',
        position: 'relative',
        overflow: 'hidden',
        ...style
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)',
          animation: 'shimmer 1.5s infinite'
        }}
      />
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
      `}</style>
    </div>
  )
}

export function SkeletonText({ lines = 3, lineHeight = '14px' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 ? '60%' : '100%'}
          height={lineHeight}
        />
      ))}
    </div>
  )
}

export function SkeletonAvatar({ size = 40 }) {
  return (
    <Skeleton
      width={size}
      height={size}
      borderRadius="50%"
    />
  )
}

export function SkeletonCard() {
  return (
    <div style={{
      padding: '20px',
      border: '1px solid var(--astrovox-border)',
      borderRadius: '12px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    }}>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <SkeletonAvatar size={40} />
        <div style={{ flex: 1 }}>
          <Skeleton width="40%" height="14px" />
          <Skeleton width="25%" height="10px" style={{ marginTop: '6px' }} />
        </div>
      </div>
      <SkeletonText lines={3} />
    </div>
  )
}
