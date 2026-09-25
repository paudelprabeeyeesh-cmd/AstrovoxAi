import { useState, useRef, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function CameraCapture({ onCapture, onClose }) {
  const [stream, setStream] = useState(null)
  const [error, setError] = useState(null)
  const [capturedImage, setCapturedImage] = useState(null)
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  useEffect(() => {
    let mounted = true
    const startCamera = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false
        })
        if (mounted) {
          setStream(mediaStream)
          if (videoRef.current) {
            videoRef.current.srcObject = mediaStream
          }
        }
      } catch (err) {
        if (mounted) setError(err.message)
      }
    }
    startCamera()
    return () => {
      mounted = false
      if (stream) {
        stream.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
    const dataUrl = canvas.toDataURL('image/png')
    setCapturedImage(dataUrl)
    onCapture?.({
      type: 'image',
      src: dataUrl,
      width: canvas.width,
      height: canvas.height,
      capturedAt: new Date().toISOString()
    })
  }, [onCapture])

  const retake = useCallback(() => {
    setCapturedImage(null)
  }, [])

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
        <Icon name="camera" size={32} style={{ color: 'var(--astrovox-error)', marginBottom: '12px' }} />
        <div style={{ fontSize: '13px', color: 'var(--astrovox-error)', marginBottom: '12px' }}>
          Camera Error: {error}
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
        position: 'relative',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)',
        overflow: 'hidden'
      }}
    >
      <button
        onClick={onClose}
        style={{
          position: 'absolute',
          top: '8px',
          right: '8px',
          zIndex: 10,
          background: 'rgba(0,0,0,0.5)',
          border: 'none',
          borderRadius: '50%',
          width: '32px',
          height: '32px',
          cursor: 'pointer',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
        aria-label="Close camera"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>

      {capturedImage ? (
        <div style={{ padding: '16px' }}>
          <img
            src={capturedImage}
            alt="Captured"
            style={{
              width: '100%',
              borderRadius: 'var(--astrovox-radius-md)',
              display: 'block'
            }}
          />
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px', justifyContent: 'center' }}>
            <button
              onClick={retake}
              style={{
                padding: '8px 16px',
                backgroundColor: 'var(--astrovox-surface-hover)',
                color: 'var(--astrovox-text)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-md)',
                cursor: 'pointer',
                fontSize: '12px',
                fontFamily: 'inherit'
              }}
            >
              Retake
            </button>
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
              Use Photo
            </button>
          </div>
        </div>
      ) : (
        <div style={{ position: 'relative' }}>
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: '100%',
              display: 'block',
              borderRadius: 'var(--astrovox-radius-lg)'
            }}
          />
          <canvas ref={canvasRef} style={{ display: 'none' }} />
          <div style={{ position: 'absolute', bottom: '16px', left: '50%', transform: 'translateX(-50%)' }}>
            <motion.button
              onClick={capturePhoto}
              whileTap={{ scale: 0.9 }}
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: 'white',
                border: '4px solid rgba(255,255,255,0.3)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              aria-label="Capture photo"
            />
          </div>
        </div>
      )}
    </div>
  )
}
