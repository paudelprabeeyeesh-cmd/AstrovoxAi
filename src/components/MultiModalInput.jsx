import { useState, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import Icon from '../design/Iconography'
import VoiceInput from './chat/VoiceInput'
import FileUpload from './chat/FileUpload'
import CameraCapture from './chat/CameraCapture'
import ScreenShare from './chat/ScreenShare'

export default function MultiModalInput({ onSend, onFileUpload, disabled = false }) {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState('text')
  const [attachments, setAttachments] = useState([])
  const [showVoice, setShowVoice] = useState(false)
  const [showFileUpload, setShowFileUpload] = useState(false)
  const [showCamera, setShowCamera] = useState(false)
  const [showScreenShare, setShowScreenShare] = useState(false)
  const textareaRef = useRef(null)

  const modes = [
    { id: 'text', icon: 'message', label: 'Text' },
    { id: 'voice', icon: 'mic', label: 'Voice' },
    { id: 'image', icon: 'image', label: 'Image' },
    { id: 'file', icon: 'paperclip', label: 'File' },
    { id: 'screen', icon: 'monitor', label: 'Screen' }
  ]

  const handleSend = useCallback(() => {
    if (!input.trim() && attachments.length === 0) return
    onSend?.({
      content: input.trim(),
      mode,
      attachments,
      timestamp: new Date().toISOString()
    })
    setInput('')
    setAttachments([])
    setMode('text')
    textareaRef.current?.focus()
  }, [input, attachments, mode, onSend])

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  const handleTranscript = useCallback((text) => {
    setInput(prev => prev ? `${prev} ${text}` : text)
    setMode('text')
    setShowVoice(false)
  }, [])

  const handleFiles = useCallback((files) => {
    const newAttachments = Array.from(files).map(file => ({
      id: crypto.randomUUID(),
      file,
      type: file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : 'file',
      name: file.name,
      size: file.size
    }))
    setAttachments(prev => [...prev, ...newAttachments])
    setShowFileUpload(false)
  }, [])

  const handleImageCapture = useCallback((dataUrl) => {
    setAttachments(prev => [...prev, {
      id: crypto.randomUUID(),
      type: 'image',
      dataUrl,
      name: 'camera-capture.png'
    }])
    setShowCamera(false)
  }, [])

  const handleScreenShare = useCallback((stream) => {
    setAttachments(prev => [...prev, {
      id: crypto.randomUUID(),
      type: 'screen',
      stream,
      name: 'screen-share'
    }])
    setShowScreenShare(false)
  }, [])

  const removeAttachment = useCallback((id) => {
    setAttachments(prev => prev.filter(a => a.id !== id))
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {attachments.length > 0 && (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {attachments.map(attachment => (
            <div
              key={attachment.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 8px',
                backgroundColor: 'var(--astrovox-surface)',
                border: '1px solid var(--astrovox-border)',
                borderRadius: 'var(--astrovox-radius-sm)',
                fontSize: '11px',
                color: 'var(--astrovox-text)'
              }}
            >
              <Icon name={attachment.type === 'image' ? 'image' : attachment.type === 'video' ? 'video' : attachment.type === 'screen' ? 'monitor' : 'file'} size={12} />
              <span style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{attachment.name}</span>
              <button
                onClick={() => removeAttachment(attachment.id)}
                style={{ background: 'none', border: 'none', color: 'var(--astrovox-text-muted)', cursor: 'pointer', padding: 0, lineHeight: 1 }}
              >
                <Icon name="x" size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      {showVoice && (
        <VoiceInput
          onTranscript={handleTranscript}
          isListening={true}
          onToggleListening={(listening) => { if (!listening) setShowVoice(false) }}
        />
      )}

      {showFileUpload && (
        <FileUpload onUpload={handleFiles} accept="image/*,video/*,.pdf,.txt,.doc,.docx" maxSize={50 * 1024 * 1024} />
      )}

      {showCamera && (
        <CameraCapture onCapture={handleImageCapture} onClose={() => setShowCamera(false)} />
      )}

      {showScreenShare && (
        <ScreenShare onShare={handleScreenShare} onClose={() => setShowScreenShare(false)} />
      )}

      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        gap: '8px',
        padding: '8px',
        backgroundColor: 'var(--astrovox-surface)',
        border: '1px solid var(--astrovox-border)',
        borderRadius: 'var(--astrovox-radius-lg)'
      }}>
        <div style={{ display: 'flex', gap: '4px' }}>
          {modes.map(m => (
            <button
              key={m.id}
              onClick={() => {
                if (m.id === 'voice') { setShowVoice(!showVoice); return }
                if (m.id === 'file') { setShowFileUpload(!showFileUpload); return }
                if (m.id === 'image') { setShowCamera(!showCamera); return }
                if (m.id === 'screen') { setShowScreenShare(!showScreenShare); return }
                setMode(m.id)
              }}
              aria-label={m.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '32px',
                height: '32px',
                background: mode === m.id && !['voice', 'file', 'image', 'screen'].includes(m.id) ? 'var(--astrovox-surface-hover)' : 'transparent',
                border: 'none',
                borderRadius: 'var(--astrovox-radius-sm)',
                color: ['voice', 'file', 'image', 'screen'].includes(m.id) && (showVoice || showFileUpload || showCamera || showScreenShare) ? 'var(--astrovox-primary)' : 'var(--astrovox-text-muted)',
                cursor: 'pointer'
              }}
            >
              <Icon name={m.icon} size={18} />
            </button>
          ))}
        </div>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message Astrovox..."
          disabled={disabled}
          rows={1}
          style={{
            flex: 1,
            minHeight: '36px',
            maxHeight: '160px',
            padding: '8px 12px',
            backgroundColor: 'var(--astrovox-bg)',
            border: '1px solid var(--astrovox-border)',
            borderRadius: 'var(--astrovox-radius-md)',
            color: 'var(--astrovox-text)',
            fontSize: '13px',
            fontFamily: 'inherit',
            resize: 'none',
            outline: 'none'
          }}
        />

        <button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && attachments.length === 0)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            background: (!input.trim() && attachments.length === 0) ? 'var(--astrovox-surface-hover)' : 'var(--astrovox-primary)',
            color: (!input.trim() && attachments.length === 0) ? 'var(--astrovox-text-muted)' : 'var(--astrovox-bg)',
            border: 'none',
            borderRadius: 'var(--astrovox-radius-md)',
            cursor: (!input.trim() && attachments.length === 0) ? 'not-allowed' : 'pointer',
            flexShrink: 0
          }}
        >
          <Icon name="send" size={18} />
        </button>
      </div>
    </div>
  )
}
