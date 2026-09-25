import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function ScreenShare({ onShare, onClose }) {
  const [stream, setStream] = useState(null)
  const [error, setError] = useState(null)
  const [isSharing, setIsSharing] = useState(false)
  const videoRef = useRef(null)

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
  }, [stream])

  const startShare = useCallback(async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'always' },
        audio: false
      })
      setStream(mediaStream)
      setIsSharing(true)
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream
      }
      mediaStream.getVideoTracks()[0].onended = () => {
        stopShare()
      }
    } catch (err) {
      setError(err.message)
    }
  }, [])

  const stopShare = useCallback(() => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
    }
    setStream(null)
    setIsSharing(false)
    onClose?.()
  }, [stream, onClose])

  if (error) {
    return (
      <div
        style={{
          padding: '24px',
          textAlign: 'center',
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)'
        }}
      >
        <Icon name="monitor" size={32} style={{ color: 'var(--astrovox-error)', marginBottom: '12px' }} />
        <div style={{ fontSize: '13px', color: 'var(--astrovox-error)', marginBottom: '12px' }}>
          Screen share error: {error}
        </div>
        <button
          onClick={onClose}
          style={{
            padding: '8px 16px',
            backgroundColor: 'var(--astrovox-primary)',
            color: 'var(--astrovox-bg)',
            border: 'none',
            borderRadius: 'var(--astrovox-radius-md)',
            cursor: 'pointer',
            fontSize: '12px',
            fontFamily: 'inherit'
          }}
        >
          Close
        </button>
      </div>
    )
  }

  return (
    <div
      style={{
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        overflow: 'hidden'
      }}
    >
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--astrovox-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Icon name="monitor" size={18} style={{ color: 'var(--astrovox-primary)' }} />
          <span style={{ fontSize: '13px', fontWeight: '600' }}>Screen Share</span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--astrovox-text-muted)',
            cursor: 'pointer',
            padding: '4px'
          }}
          aria-label="Close screen share"
        >
          <Icon name="x" size={18} />
        </button>
      </div>

      {!isSharing ? (
        <div style={{ padding: '32px', textAlign: 'center' }}>
          <Icon name="monitor" size={48} style={{ color: 'var(--astrovox-text-muted)', marginBottom: '16px' }} />
          <div style={{ fontSize: '13px', color: 'var(--astrovox-text)', marginBottom: '16px' }}>
            Share your screen with the AI assistant
          </div>
          <motion.button
            onClick={startShare}
            whileTap={{ scale: 0.95 }}
            style={{
              padding: '12px 24px',
              backgroundColor: 'var(--astrovox-primary)',
              color: 'var(--astrovox-bg)',
              border: 'none',
              borderRadius: 'var(--astrovox-radius-md)',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: '600',
              fontFamily: 'inherit'
            }}
          >
            Start Sharing
          </motion.button>
        </div>
      ) : (
        <div>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: '100%',
              maxHeight: '400px',
              display: 'block',
              backgroundColor: 'var(--astrovox-code)'
            }}
          />
          <div style={{ padding: '12px 16px', display: 'flex', justifyContent: 'center' }}>
            <motion.button
              onClick={stopShare}
              whileTap={{ scale: 0.95 }}
              style={{
                padding: '10px 24px',
                backgroundColor: 'var(--astrovox-error)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--astrovox-radius-md)',
                cursor: 'pointer',
                fontSize: '12px',
                fontWeight: '600',
                fontFamily: 'inherit'
              }}
            >
              Stop Sharing
            </motion.button>
          </div>
        </div>
      )}
    </div>
  )
}
