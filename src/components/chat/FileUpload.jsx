import { useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Icon from '../../design/Iconography'

export default function FileUpload({ onUpload, accept = '*', maxSize = 10 * 1024 * 1024 }) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState({})
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const validateFile = useCallback((file) => {
    if (maxSize && file.size > maxSize) {
      setError(`File too large. Max size: ${(maxSize / 1024 / 1024).toFixed(1)}MB`)
      return false
    }
    setError(null)
    return true
  }, [maxSize])

  const handleFiles = useCallback(async (files) => {
    const validFiles = Array.from(files).filter(validateFile)
    if (validFiles.length === 0) return

    for (const file of validFiles) {
      const fileId = crypto.randomUUID()
      setUploadProgress(prev => ({ ...prev, [fileId]: 0 }))

      const reader = new FileReader()
      reader.onloadstart = () => setUploadProgress(prev => ({ ...prev, [fileId]: 10 }))
      reader.onprogress = (e) => {
        if (e.lengthComputable) {
          const progress = Math.round((e.loaded / e.total) * 100)
          setUploadProgress(prev => ({ ...prev, [fileId]: progress }))
        }
      }
      reader.onload = () => {
        setUploadProgress(prev => ({ ...prev, [fileId]: 100 }))
        setTimeout(() => {
          setUploadProgress(prev => {
            const next = { ...prev }
            delete next[fileId]
            return next
          })
        }, 1000)
        onUpload?.({
          id: fileId,
          name: file.name,
          size: file.size,
          type: file.type,
          content: reader.result,
          uploadedAt: new Date().toISOString()
        })
      }
      reader.readAsDataURL(file)
    }
  }, [validateFile, onUpload])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files)
    }
  }, [handleFiles])

  const handleInputChange = useCallback((e) => {
    if (e.target.files.length > 0) {
      handleFiles(e.target.files)
    }
  }, [handleFiles])

  return (
    <div style={{ width: '100%' }}>
      <motion.div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: `2px dashed ${isDragging ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`,
          borderRadius: 'var(--astrovox-radius-lg)',
          padding: '32px',
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'all 0.2s',
          backgroundColor: isDragging ? 'var(--astrovox-surface-hover)' : 'transparent'
        }}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
        aria-label="Upload files"
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple
          onChange={handleInputChange}
          style={{ display: 'none' }}
          aria-hidden="true"
        />
        <Icon name="upload" size={32} style={{ color: 'var(--astrovox-primary)', marginBottom: '12px' }} />
        <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--astrovox-text)', marginBottom: '4px' }}>
          {isDragging ? 'Drop files here' : 'Drag and drop files here'}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>
          or click to browse • Max {(maxSize / 1024 / 1024).toFixed(0)}MB
        </div>
      </motion.div>

      {error && (
        <div
          style={{
            marginTop: '8px',
            padding: '8px 12px',
            backgroundColor: 'var(--astrovox-error-bg)',
            border: '1px solid var(--astrovox-error)',
            borderRadius: 'var(--astrovox-radius-md)',
            color: 'var(--astrovox-error)',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          <Icon name="alert" size={14} />
          {error}
        </div>
      )}

      <AnimatePresence>
        {Object.entries(uploadProgress).map(([fileId, progress]) => (
          <motion.div
            key={fileId}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              marginTop: '8px',
              padding: '8px 12px',
              backgroundColor: 'var(--astrovox-surface)',
              border: '1px solid var(--astrovox-border)',
              borderRadius: 'var(--astrovox-radius-md)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '11px', color: 'var(--astrovox-text)' }}>Uploading...</span>
              <span style={{ fontSize: '11px', color: 'var(--astrovox-text-muted)' }}>{progress}%</span>
            </div>
            <div
              style={{
                height: '4px',
                backgroundColor: 'var(--astrovox-border)',
                borderRadius: '2px',
                overflow: 'hidden'
              }}
            >
              <motion.div
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
                style={{
                  height: '100%',
                  backgroundColor: 'var(--astrovox-primary)',
                  borderRadius: '2px'
                }}
              />
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
