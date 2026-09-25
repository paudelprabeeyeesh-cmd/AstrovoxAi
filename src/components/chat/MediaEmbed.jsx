import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function MediaEmbed({ type, src, alt = '', width = '100%', height = 'auto' }) {
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  const handleLoad = () => setIsLoading(false)
  const handleError = () => { setIsLoading(false); setHasError(true) }

  if (hasError) {
    return (
      <div
        style={{
          padding: '24px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid var(--astrovox-error)',
          borderRadius: 'var(--astrovox-radius-md)',
          textAlign: 'center',
          color: 'var(--astrovox-error)',
          fontSize: '12px'
        }}
      >
        <Icon name="alert" size={20} style={{ marginBottom: '8px' }} />
        <div>Failed to load {type}</div>
      </div>
    )
  }

  if (type === 'image') {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        style={{
          marginTop: '12px',
          borderRadius: 'var(--astrovox-radius-lg)',
          overflow: 'hidden',
          border: '1px solid var(--astrovox-border)'
        }}
      >
        {isLoading && (
          <div
            style={{
              padding: '40px',
              textAlign: 'center',
              color: 'var(--astrovox-text-muted)',
              fontSize: '12px'
            }}
          >
            <div
              style={{
                width: '24px',
                height: '24px',
                border: '2px solid var(--astrovox-primary)',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
                margin: '0 auto 8px'
              }}
            />
            Loading image...
          </div>
        )}
        <img
          src={src}
          alt={alt}
          onLoad={handleLoad}
          onError={handleError}
          style={{
            maxWidth: width,
            maxHeight: '400px',
            display: isLoading ? 'none' : 'block',
            borderRadius: 'var(--astrovox-radius-lg)'
          }}
        />
      </motion.div>
    )
  }

  if (type === 'audio') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          marginTop: '12px',
          padding: '12px',
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px'
        }}
      >
        <Icon name="audio" size={24} style={{ color: 'var(--astrovox-primary)', flexShrink: 0 }} />
        <audio
          controls
          style={{ flex: 1, height: '36px' }}
          onLoadedData={handleLoad}
          onError={handleError}
        >
          <source src={src} />
        </audio>
      </motion.div>
    )
  }

  if (type === 'video') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          marginTop: '12px',
          borderRadius: 'var(--astrovox-radius-lg)',
          overflow: 'hidden',
          border: '1px solid var(--astrovox-border)'
        }}
      >
        {isLoading && (
          <div
            style={{
              padding: '40px',
              textAlign: 'center',
              color: 'var(--astrovox-text-muted)',
              fontSize: '12px'
            }}
          >
            <div
              style={{
                width: '24px',
                height: '24px',
                border: '2px solid var(--astrovox-primary)',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
                margin: '0 auto 8px'
              }}
            />
            Loading video...
          </div>
        )}
        <video
          controls
          onLoadedData={handleLoad}
          onError={handleError}
          style={{
            maxWidth: width,
            maxHeight: '400px',
            display: isLoading ? 'none' : 'block',
            borderRadius: 'var(--astrovox-radius-lg)'
          }}
        >
          <source src={src} />
        </video>
      </motion.div>
    )
  }

  if (type === 'file') {
    return (
      <motion.a
        href={src}
        target="_blank"
        rel="noopener noreferrer"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          marginTop: '12px',
          padding: '12px 16px',
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          color: 'var(--astrovox-text)',
          textDecoration: 'none',
          fontSize: '13px'
        }}
      >
        <Icon name="file" size={24} style={{ color: 'var(--astrovox-primary)', flexShrink: 0 }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: '600', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {alt || 'Download file'}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)', marginTop: '2px' }}>
            Click to download
          </div>
        </div>
        <Icon name="download" size={16} style={{ color: 'var(--astrovox-text-muted)', flexShrink: 0 }} />
      </motion.a>
    )
  }

  return null
}
