import { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useChatHistory } from '../../hooks/useChatHistory'
import StreamingMessage from '../chat/StreamingMessage.jsx'
import MessageActions from '../chat/MessageActions.jsx'
import MarkdownRenderer from '../chat/MarkdownRenderer.jsx'
import FileUpload from '../chat/FileUpload.jsx'
import VoiceInput from '../chat/VoiceInput.jsx'
import VoiceOutput from '../chat/VoiceOutput.jsx'
import CameraCapture from '../chat/CameraCapture.jsx'
import ScreenShare from '../chat/ScreenShare.jsx'
import Whiteboard from '../chat/Whiteboard.jsx'
import MultiChatTabs from '../workspace/MultiChatTabs.jsx'
import ChatBranching from '../workspace/ChatBranching.jsx'
import FolderSystem from '../workspace/FolderSystem.jsx'
import TeamWorkspace from '../workspace/TeamWorkspace.jsx'
import SharedConversations from '../workspace/SharedConversations.jsx'
import NotificationCenter from '../ui/NotificationCenter.jsx'
import KeyboardShortcuts from '../ui/KeyboardShortcuts.jsx'
import A11yProvider, { SkipLink, useA11y } from '../ui/A11yProvider.jsx'
import Icon from '../../design/Iconography'

const MOCK_NOTIFICATIONS = [
  { id: '1', title: 'New message', message: 'You have a new message from the team', type: 'info', timestamp: Date.now() - 60000, read: false },
  { id: '2', title: 'Model update', message: 'gpt-4-turbo has been updated', type: 'info', timestamp: Date.now() - 3600000, read: false },
  { id: '3', title: 'Usage warning', message: 'You are approaching your monthly limit', type: 'warning', timestamp: Date.now() - 7200000, read: true }
]

const buttonStyle = {
  padding: '4px 10px',
  backgroundColor: 'var(--astrovox-surface-hover)',
  color: 'var(--astrovox-text)',
  border: '1px solid var(--astrovox-border)',
  borderRadius: 'var(--astrovox-radius-sm)',
  cursor: 'pointer',
  fontSize: '11px',
  fontFamily: 'inherit'
}

export default function ChatInterface({ session, conversationId, model = 'gpt-4' }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [typing, setTyping] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [isStreamComplete, setIsStreamComplete] = useState(true)
  const [copiedMessageId, setCopiedMessageId] = useState(null)
  const [editingMessageId, setEditingMessageId] = useState(null)
  const [editContent, setEditContent] = useState('')
  const [showVoice, setShowVoice] = useState(false)
  const [showCamera, setShowCamera] = useState(false)
  const [showScreenShare, setShowScreenShare] = useState(false)
  const [showWhiteboard, setShowWhiteboard] = useState(false)
  const [showFileUpload, setShowFileUpload] = useState(false)
  const [showBranching, setShowBranching] = useState(false)
  const [activeTabs, setActiveTabs] = useState([{ id: 'default', title: 'New Chat' }])
  const [activeTabId, setActiveTabId] = useState('default')
  const [activeFolder, setActiveFolder] = useState(null)
  const [folders, setFolders] = useState([])
  const [todos, setTodos] = useState([])
  const [showTeamWorkspace, setShowTeamWorkspace] = useState(false)
  const [showShared, setShowShared] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const { history, branches, addMessage, createBranch, addBranchMessage, clearHistory } = useChatHistory()
  const { announce } = useA11y()

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingContent, scrollToBottom])

  const simulateStream = useCallback((text) => {
    setStreamingContent('')
    setIsStreamComplete(false)
    setTyping(true)
    let index = 0
    const interval = setInterval(() => {
      setStreamingContent(prev => prev + text[index])
      index++
      if (index >= text.length) {
        clearInterval(interval)
        setTyping(false)
        setIsStreamComplete(true)
        setStreamingContent(text)
      }
    }, 20)
    return () => clearInterval(interval)
  }, [])

  async function handleSendMessage(e) {
    e.preventDefault()
    if (!input.trim() && !showFileUpload) return
    const userMessage = input.trim()
    setInput('')
    setShowFileUpload(false)

    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    addMessage(userMsg)
    announce('Message sent')

    const aiResponseText = "This is a simulated AI response demonstrating the streaming capabilities of the chat interface. The response includes **markdown formatting**, `code blocks`, and rich content rendering."
    await simulateStream(aiResponseText)

    const aiMsg = {
      id: Date.now() + 1,
      role: 'assistant',
      content: aiResponseText,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, aiMsg])
    addMessage(aiMsg)
    announce('AI response received')
  }

  function handleRetry(message) {
    if (message.role === 'assistant') {
      simulateStream(message.content + ' [retried]')
    }
  }

  function handleEdit(message) {
    setEditingMessageId(message.id)
    setEditContent(message.content)
    inputRef.current?.focus()
  }

  function handleSaveEdit(message) {
    if (editContent.trim()) {
      setMessages(prev => prev.map(m => m.id === message.id ? { ...m, content: editContent.trim() } : m))
    }
    setEditingMessageId(null)
    setEditContent('')
  }

  function handleDelete(message) {
    setMessages(prev => prev.filter(m => m.id !== message.id))
    announce('Message deleted')
  }

  function handleBranch(message) {
    createBranch(message.id, `Branch from message ${message.id}`)
    announce(`Created branch from message`)
  }

  function handleFileUpload(file) {
    const userMsg = {
      id: Date.now(),
      role: 'user',
      content: `Uploaded file: ${file.name}`,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMsg])
    announce(`File uploaded: ${file.name}`)
  }

  function handleNewTab() {
    const newTab = { id: crypto.randomUUID(), title: 'New Chat' }
    setActiveTabs(prev => [...prev, newTab])
    setActiveTabId(newTab.id)
    setMessages([])
  }

  function handleCloseTab(id) {
    if (activeTabs.length === 1) return
    setActiveTabs(prev => prev.filter(t => t.id !== id))
    if (activeTabId === id) {
      const remaining = activeTabs.filter(t => t.id !== id)
      setActiveTabId(remaining[0]?.id || 'default')
    }
  }

  function handleCreateFolder() {
    const name = prompt('Folder name:')
    if (name?.trim()) {
      setFolders(prev => [...prev, { id: crypto.randomUUID(), name: name.trim(), createdAt: new Date().toISOString() }])
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  return (
    <A11yProvider>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--astrovox-bg)' }}>
        <SkipLink targetId="main-content">Skip to main content</SkipLink>

        <div
          id="main-content"
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            backgroundColor: 'var(--astrovox-bg)'
          }}
        >
          {activeTabs.length > 1 && (
            <MultiChatTabs
              conversations={activeTabs}
              activeId={activeTabId}
              onSelect={setActiveTabId}
              onNew={handleNewTab}
              onClose={handleCloseTab}
            />
          )}

          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div
                style={{
                  padding: '12px 20px',
                  borderBottom: '1px solid var(--astrovox-border)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  backgroundColor: 'rgba(4, 8, 20, 0.5)',
                  backdropFilter: 'blur(8px)'
                }}
              >
                <h3 style={{ margin: 0, fontSize: '14px', color: 'var(--astrovox-accent)', letterSpacing: '1px', fontWeight: '600' }}>
                  🤖 AI CHAT INTERFACE
                </h3>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button onClick={() => setShowShortcuts(true)} style={{ ...iconButtonStyle }} aria-label="Keyboard shortcuts">
                    <Icon name="keyboard" size={16} />
                  </button>
                  <button onClick={() => setShowNotifications(true)} style={{ ...iconButtonStyle }} aria-label="Notifications">
                    <Icon name="bell" size={16} />
                  </button>
                </div>
              </div>

              <div
                style={{
                  flex: 1,
                  overflowY: 'auto',
                  padding: '20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px'
                }}
                role="log"
                aria-live="polite"
                aria-label="Chat messages"
              >
                {messages.length === 0 && !streamingContent && (
                  <div style={{ textAlign: 'center', color: 'var(--astrovox-text-muted)', fontSize: '13px', padding: '40px 20px' }}>
                    <div style={{ fontSize: '32px', marginBottom: '12px' }}>🛸</div>
                    <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px', color: 'var(--astrovox-text)' }}>Start a Conversation</div>
                    <div>Type a message or use voice input to begin</div>
                    <button
                      onClick={() => setShowShortcuts(true)}
                      style={{ marginTop: '12px', padding: '8px 16px', backgroundColor: 'var(--astrovox-primary)', color: 'var(--astrovox-bg)', border: 'none', borderRadius: 'var(--astrovox-radius-md)', cursor: 'pointer', fontSize: '12px', fontFamily: 'inherit' }}
                    >
                      View Keyboard Shortcuts
                    </button>
                  </div>
                )}

                {messages.map(msg => (
                  <div
                    key={msg.id}
                    style={{
                      display: 'flex',
                      justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      position: 'relative',
                      maxWidth: '75%'
                    }}
                  >
                    <div
                      style={{
                        padding: '12px 16px',
                        borderRadius: 'var(--astrovox-radius-lg)',
                        backgroundColor: msg.role === 'user' ? 'var(--astrovox-primary)' : 'var(--astrovox-surface)',
                        color: msg.role === 'user' ? 'var(--astrovox-bg)' : 'var(--astrovox-text)',
                        border: msg.role === 'user' ? 'none' : '1px solid var(--astrovox-border)',
                        fontSize: '13px',
                        lineHeight: '1.6',
                        wordWrap: 'break-word'
                      }}
                    >
                      {editingMessageId === msg.id ? (
                        <div>
                          <textarea
                            autoFocus
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            style={{ width: '100%', minHeight: '72px', boxSizing: 'border-box', resize: 'vertical', background: 'var(--astrovox-bg)', color: 'var(--astrovox-text)', border: '1px solid var(--astrovox-primary)', borderRadius: 'var(--astrovox-radius-md)', padding: '8px', fontFamily: 'inherit' }}
                          />
                          <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                            <button onClick={() => handleSaveEdit(msg)} style={{ ...buttonStyle }}>Save</button>
                            <button onClick={() => setEditingMessageId(null)} style={{ ...buttonStyle }}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        <MarkdownRenderer content={msg.content} />
                      )}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', gap: '8px' }}>
                        <span style={{ fontSize: '10px', opacity: 0.7 }}>
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </span>
                        <MessageActions
                          message={msg}
                          onCopy={() => { navigator.clipboard.writeText(msg.content); announce('Message copied') }}
                          onEdit={handleEdit}
                          onDelete={handleDelete}
                          onRetry={handleRetry}
                          onBranch={handleBranch}
                        />
                      </div>
                    </div>
                  </div>
                ))}

                {streamingContent && !isStreamComplete && (
                  <StreamingMessage
                    content={streamingContent}
                    isComplete={isStreamComplete}
                    onRetry={() => simulateStream(streamingContent)}
                    model={model}
                  />
                )}

                {typing && (
                  <div style={{ display: 'flex', gap: '6px', padding: '12px 16px', backgroundColor: 'var(--astrovox-surface)', borderRadius: 'var(--astrovox-radius-lg)', width: 'fit-content' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--astrovox-primary)', animation: 'bounce 1.4s infinite' }} />
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--astrovox-primary)', animation: 'bounce 1.4s infinite 0.2s' }} />
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--astrovox-primary)', animation: 'bounce 1.4s infinite 0.4s' }} />
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              <form onSubmit={handleSendMessage} style={{ padding: '16px 20px', borderTop: '1px solid var(--astrovox-border)', backgroundColor: 'rgba(4, 8, 20, 0.5)', backdropFilter: 'blur(8px)' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
                  <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {showFileUpload && (
                      <FileUpload onUpload={handleFileUpload} />
                    )}
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
                      <textarea
                        ref={inputRef}
                        placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={loading || typing}
                        style={{
                          flex: 1,
                          padding: '12px 16px',
                          minHeight: '46px',
                          maxHeight: '140px',
                          resize: 'vertical',
                          borderRadius: 'var(--astrovox-radius-full)',
                          backgroundColor: 'var(--astrovox-bg)',
                          border: '1px solid var(--astrovox-border)',
                          color: 'var(--astrovox-text)',
                          fontFamily: 'var(--astrovox-font-sans)',
                          fontSize: '13px',
                          outline: 'none',
                          opacity: loading || typing ? 0.5 : 1
                        }}
                        onFocus={(e) => e.target.style.borderColor = 'var(--astrovox-primary)'}
                        onBlur={(e) => e.target.style.borderColor = 'var(--astrovox-border)'}
                        aria-label="Message input"
                      />
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <button type="button" onClick={() => setShowFileUpload(!showFileUpload)} style={{ ...iconButtonStyle }} aria-label="Upload file">
                          <Icon name="upload" size={16} />
                        </button>
                        <button type="button" onClick={() => setShowVoice(!showVoice)} style={{ ...iconButtonStyle, ...(showVoice ? activeIconStyle : {}) }} aria-label="Voice input">
                          <Icon name="mic" size={16} />
                        </button>
                        <button type="button" onClick={() => setShowCamera(true)} style={{ ...iconButtonStyle }} aria-label="Camera">
                          <Icon name="camera" size={16} />
                        </button>
                        <button type="button" onClick={() => setShowScreenShare(true)} style={{ ...iconButtonStyle }} aria-label="Screen share">
                          <Icon name="monitor" size={16} />
                        </button>
                        <button type="submit" disabled={loading || typing || !input.trim()} style={{ ...sendButtonStyle, opacity: loading || typing || !input.trim() ? 0.5 : 1 }}>
                          SEND
                        </button>
                      </div>
                    </div>
                    {showVoice && <VoiceInput onTranscript={setInput} onToggleListening={setShowVoice} />}
                  </div>
                </div>
              </form>

              {messages.length > 0 && <VoiceOutput text={messages[messages.length - 1]?.content} />}
            </div>
          </div>
        </div>

        <NotificationCenter notifications={MOCK_NOTIFICATIONS} />

        {showShortcuts && (
          <KeyboardShortcutsModal onClose={() => setShowShortcuts(false)} />
        )}

        {showCamera && (
          <CameraCapture onCapture={(file) => { setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: `[Camera: ${file.type}]`, timestamp: new Date().toISOString() }]); setShowCamera(false) }} onClose={() => setShowCamera(false)} />
        )}

        {showScreenShare && (
          <ScreenShare onShare={() => {}} onClose={() => setShowScreenShare(false)} />
        )}

        {showWhiteboard && (
          <Whiteboard onSave={(data) => { setMessages(prev => [...prev, { id: Date.now(), role: 'user', content: `[Whiteboard saved]`, timestamp: new Date().toISOString() }]); setShowWhiteboard(false) }} onClose={() => setShowWhiteboard(false)} />
        )}
      </div>
    </A11yProvider>
  )
}

const iconButtonStyle = {
  padding: '8px',
  backgroundColor: 'transparent',
  border: '1px solid var(--astrovox-border)',
  borderRadius: 'var(--astrovox-radius-md)',
  color: 'var(--astrovox-text-muted)',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}

const activeIconStyle = {
  backgroundColor: 'var(--astrovox-primary)',
  color: 'var(--astrovox-bg)',
  borderColor: 'var(--astrovox-primary)'
}

const sendButtonStyle = {
  padding: '0 24px',
  backgroundColor: 'var(--astrovox-primary)',
  color: 'var(--astrovox-bg)',
  border: 'none',
  borderRadius: 'var(--astrovox-radius-full)',
  cursor: 'pointer',
  fontWeight: '700',
  fontSize: '12px',
  letterSpacing: '0.5px',
  transition: 'all 0.2s',
  fontFamily: 'inherit'
}

function KeyboardShortcutsModal({ onClose }) {
  const shortcuts = [
    { keys: ['Enter'], description: 'Send message' },
    { keys: ['Shift', 'Enter'], description: 'New line' },
    { keys: ['Ctrl', 'N'], description: 'New conversation' },
    { keys: ['Ctrl', 'K'], description: 'Search' },
    { keys: ['Ctrl', 'T'], description: 'Toggle theme' },
    { keys: ['Ctrl', 'I'], description: 'Focus input' },
    { keys: ['Escape'], description: 'Close dialog' },
    { keys: ['?'], description: 'Show shortcuts' }
  ]

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 2000
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--astrovox-surface)',
          border: '1px solid var(--astrovox-border)',
          borderRadius: 'var(--astrovox-radius-lg)',
          padding: '24px',
          maxWidth: '500px',
          width: '90%',
          maxHeight: '80vh',
          overflowY: 'auto'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: '700' }}>Keyboard Shortcuts</h2>
          <button onClick={onClose} style={{ ...iconButtonStyle }}><Icon name="x" size={18} /></button>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {shortcuts.map(s => (
            <div key={s.description} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--astrovox-border)' }}>
              <span style={{ fontSize: '13px', color: 'var(--astrovox-text)' }}>{s.description}</span>
              <div style={{ display: 'flex', gap: '4px' }}>
                {s.keys.map((key, i) => (
                  <kbd key={i} style={{
                    padding: '2px 8px',
                    backgroundColor: 'var(--astrovox-bg)',
                    border: '1px solid var(--astrovox-border)',
                    borderRadius: 'var(--astrovox-radius-sm)',
                    color: 'var(--astrovox-text)',
                    fontSize: '11px',
                    fontFamily: 'var(--astrovox-font-mono)'
                  }}>{key}</kbd>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
