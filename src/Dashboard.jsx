import { useState, useEffect, useCallback } from 'react'
import { supabase } from './supabase'
import Sidebar from './Sidebar'
import Chat from './Chat'
import Telemetry from './telemetry'
import TerminalConsole from './terminalconsole'
import MemoryPanel from './MemoryPanel'
import SettingsPanel from './SettingsPanel'
import MultiversePanel from './components/multiverse/MultiversePanel'
import HolographicPanel from './components/holographic/HolographicPanel'
import QuantumHolographicSystem from './components/quantum/QuantumHolographicSystem'
import { ToastProvider, useToast } from './components/ui/Toast'
import { CommandPalette } from './components/ui/CommandPalette'
import { KeyboardShortcutCheatsheet } from './components/ui/KeyboardShortcutCheatsheet'
import SupportPanel from './components/support/SupportPanel'
import OnboardingFlow from './components/support/OnboardingFlow'
import TutorialsPanel from './components/support/TutorialsPanel'
import CustomerPortal from './components/support/CustomerPortal'
import StatusPage from './components/support/StatusPage'
import AnalyticsPanel from './components/support/AnalyticsPanel'
import HealthScore from './components/support/HealthScore'
import NpsSurvey from './components/support/NpsSurvey'
import OmnipresentSystem from './components/omnipresent/OmnipresentSystem'
import OmniscientSearch from './components/transcendent/OmniscientSearch'
import ThoughtPrediction from './components/transcendent/ThoughtPrediction'
import FutureForecast from './components/transcendent/FutureForecast'
import UniversalTranslation from './components/transcendent/UniversalTranslation'
import OmnipresentMonitoring from './components/transcendent/OmnipresentMonitoring'
import InfiniteScroll from './components/transcendent/InfiniteScroll'
import RealityWarpingSearch from './components/transcendent/RealityWarpingSearch'
import UniverseSandbox from './components/transcendent/UniverseSandbox'
import OmnipotentAssistant from './components/transcendent/OmnipotentAssistant'

function DashboardInner({ session }) {
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [terminalLogs, setTerminalLogs] = useState([
    '>> ASTROVOX OS v2.0.6 INITIALIZED SUCCESS',
    '>> Type /help to list available mainframe overrides.'
  ])
  const [totalConversations, setTotalConversations] = useState(0)
  const [dbStatus, setDbStatus] = useState('online')
  const [activePanel, setActivePanel] = useState('chat')
  const [selectedModel, setSelectedModel] = useState('gpt-4')
  const [showCommandPalette, setShowCommandPalette] = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)

  const { addToast } = useToast()

  const loadUserStats = useCallback(async () => {
    try {
      const { count, error } = await supabase
        .from('conversations')
        .select('*', { count: 'exact', head: true })
        .eq('user_id', session.user.id)
        .eq('is_deleted', false)

      if (error) throw error
      setTotalConversations(count || 0)
      setDbStatus('online')
    } catch (err) {
      console.error('Failed to load stats:', err)
      setDbStatus('offline')
    }
  }, [session.user.id])

  useEffect(() => {
    if (session) {
      loadUserStats()
    }
  }, [session, loadUserStats])

  const handleCommandSelect = useCallback((cmd) => {
    addToast(`Executing: ${cmd.label}`, { type: 'info' })
    if (cmd.id === 'logout') {
      supabase.auth.signOut()
    }
  }, [addToast])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowCommandPalette(prev => !prev)
      }
      if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
        setShowShortcuts(prev => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      backgroundColor: '#02040a',
      color: '#e2e8f0',
      fontFamily: "'Inter', 'Segoe UI', monospace",
      backgroundImage: 'radial-gradient(ellipse at 50% 0%, rgba(6, 182, 212, 0.05) 0%, transparent 70%)'
    }}>
      {/* Sidebar */}
      <Sidebar
        session={session}
        onSelectConversation={setCurrentConversationId}
        currentConversationId={currentConversationId}
      />

      {/* Main Content */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }}>
        {/* Top Header */}
        <header style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'rgba(4, 8, 20, 0.7)',
          backdropFilter: 'blur(12px)',
          border: '1px solid #1e293b',
          borderRadius: '0 0 16px 0',
          padding: '16px 24px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)'
        }}>
          <div>
            <h2 style={{
              margin: 0,
              fontSize: '18px',
              letterSpacing: '1px',
              background: 'linear-gradient(135deg, #67e8f9, #06b6d4)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              color: 'transparent'
            }}>
              🛸 ASTRAVOX // MAIN FRAME
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b' }}>
              OPERATOR: <span style={{ color: '#f472b6' }}>{session.user.email}</span>
              <span style={{ marginLeft: '16px' }}>
                <span style={{ color: '#34d399' }}>●</span> {dbStatus}
              </span>
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              onClick={() => setShowCommandPalette(true)}
              style={{
                padding: '8px 16px',
                backgroundColor: 'transparent',
                border: '1px solid #1e293b',
                color: '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
              title="Command palette (Cmd+K)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              Search
            </button>
            <button
              onClick={() => setShowShortcuts(true)}
              style={{
                padding: '8px 16px',
                backgroundColor: 'transparent',
                border: '1px solid #1e293b',
                color: '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
              title="Keyboard shortcuts (?)"
            >
              Shortcuts
            </button>
            <button
              onClick={() => setActivePanel('chat')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'chat' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'chat' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              💬 CHAT
            </button>
            <button
              onClick={() => setActivePanel('memory')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'memory' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'memory' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🧠 MEMORY
            </button>
            <button
              onClick={() => setActivePanel('settings')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'settings' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'settings' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              ⚙️ SETTINGS
            </button>
            <button
              onClick={() => setActivePanel('quantum')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'quantum' ? '#a78bfa' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'quantum' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              ⚛️ QUANTUM
            </button>
            <button
              onClick={() => setActivePanel('holographic')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'holographic' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'holographic' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              💎 HOLOGRAPHIC
            </button>
            <button
              onClick={() => setActivePanel('support')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'support' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'support' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🛟 SUPPORT
            </button>
            <button
              onClick={() => setActivePanel('onboarding')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'onboarding' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'onboarding' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🚀 ONBOARDING
            </button>
            <button
              onClick={() => setActivePanel('tutorials')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'tutorials' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'tutorials' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📖 TUTORIALS
            </button>
            <button
              onClick={() => setActivePanel('portal')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'portal' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'portal' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🏠 PORTAL
            </button>
            <button
              onClick={() => setActivePanel('status')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'status' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'status' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📊 STATUS
            </button>
            <button
              onClick={() => setActivePanel('analytics')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'analytics' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'analytics' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📈 ANALYTICS
            </button>
            <button
              onClick={() => setActivePanel('health')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'health' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'health' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              ❤️ HEALTH
            </button>
            <button
              onClick={() => setActivePanel('nps')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'nps' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'nps' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📋 NPS
            </button>
            <button
              onClick={() => setActivePanel('omnipresent')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'omnipresent' ? '#a78bfa' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'omnipresent' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🌐 OMNIPRESENT
            </button>
            <button
              onClick={() => setActivePanel('omniscient')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'omniscient' ? '#f59e0b' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'omniscient' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              👁️ OMNISCIENT
            </button>
            <button
              onClick={() => setActivePanel('prediction')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'prediction' ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'prediction' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🔮 PREDICTION
            </button>
            <button
              onClick={() => setActivePanel('translation')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'translation' ? '#22c55e' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'translation' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🌐 TRANSLATION
            </button>
            <button
              onClick={() => setActivePanel('monitoring')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'monitoring' ? '#ef4444' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'monitoring' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📡 MONITORING
            </button>
            <button
              onClick={() => setActivePanel('sandbox')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'sandbox' ? '#a78bfa' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'sandbox' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              📦 SANDBOX
            </button>
            <button
              onClick={() => setActivePanel('omnipotent')}
              style={{
                padding: '8px 16px',
                backgroundColor: activePanel === 'omnipotent' ? '#f59e0b' : 'transparent',
                border: '1px solid #1e293b',
                color: activePanel === 'omnipotent' ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              🛐 OMNIPOTENT
            </button>
            <button
              onClick={() => supabase.auth.signOut()}
              style={{
                padding: '8px 20px',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid #ef4444',
                color: '#f87171',
                borderRadius: '40px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s',
                letterSpacing: '0.5px'
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = 'rgba(239, 68, 68, 0.25)'
                e.target.style.transform = 'scale(1.02)'
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = 'rgba(239, 68, 68, 0.15)'
                e.target.style.transform = 'scale(1)'
              }}
            >
              DISCONNECT
            </button>
          </div>
        </header>

        {/* Main Content Area */}
        <div style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: activePanel === 'chat' ? '1fr 1fr' : '1fr',
          gap: '16px',
          padding: '16px',
          overflow: 'hidden'
        }}>
          {/* Left Panel */}
          {activePanel === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <Chat
                session={session}
                conversationId={currentConversationId}
                model={selectedModel}
                onConversationChange={(id) => setCurrentConversationId(id)}
              />
            </div>
          )}

          {activePanel === 'memory' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <MemoryPanel session={session} />
            </div>
          )}

          {activePanel === 'settings' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <SettingsPanel session={session} onModelChange={setSelectedModel} />
            </div>
          )}

          {activePanel === 'multiverse' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <MultiversePanel />
            </div>
          )}

          {activePanel === 'quantum' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <QuantumHolographicSystem />
            </div>
          )}

          {activePanel === 'holographic' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <HolographicPanel />
            </div>
          )}

          {activePanel === 'support' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <SupportPanel session={session} />
            </div>
          )}

          {activePanel === 'onboarding' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <OnboardingFlow onComplete={() => setActivePanel('chat')} />
            </div>
          )}

          {activePanel === 'tutorials' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <TutorialsPanel />
            </div>
          )}

          {activePanel === 'portal' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <CustomerPortal session={session} />
            </div>
          )}

          {activePanel === 'status' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <StatusPage />
            </div>
          )}

          {activePanel === 'analytics' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <AnalyticsPanel />
            </div>
          )}

          {activePanel === 'health' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <HealthScore />
            </div>
          )}

          {activePanel === 'nps' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <NpsSurvey />
            </div>
          )}

          {activePanel === 'omnipresent' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <OmnipresentSystem session={session} />
            </div>
          )}

          {activePanel === 'omniscient' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <OmniscientSearch />
            </div>
          )}

          {activePanel === 'prediction' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <ThoughtPrediction userId={session.user.id} />
              <FutureForecast />
            </div>
          )}

          {activePanel === 'translation' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <UniversalTranslation />
            </div>
          )}

          {activePanel === 'monitoring' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <OmnipresentMonitoring />
            </div>
          )}

          {activePanel === 'sandbox' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <UniverseSandbox />
            </div>
          )}

          {activePanel === 'omnipotent' && (
            <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <OmnipotentAssistant />
            </div>
          )}

          {/* Right Panel: Terminal & Telemetry (only in chat mode) */}
          {activePanel === 'chat' && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              overflow: 'hidden'
            }}>
              <TerminalConsole
                userEmail={session.user.email}
                totalItems={totalConversations}
                history={terminalLogs}
                setHistory={setTerminalLogs}
              />
              <Telemetry
                totalPackets={totalConversations}
                dbStatus={dbStatus}
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          paddingTop: '16px',
          borderTop: '1px solid #1e293b',
          textAlign: 'center',
          fontSize: '10px',
          color: '#475569',
          letterSpacing: '0.5px',
          padding: '16px'
        }}>
          ASTRAVOX PRIME v2.0.6 · Built by Astrovox Team
          <span style={{ margin: '0 12px' }}>|</span>
          <span style={{ color: '#334155' }}>SYSTEM STATUS: {dbStatus === 'online' ? '🟢 OPERATIONAL' : '⚠️ DEGRADED'}</span>
        </div>
      </div>

      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
        onSelect={handleCommandSelect}
      />
      <KeyboardShortcutCheatsheet
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
    </div>
  )
}

export default function Dashboard({ session }) {
  return (
    <ToastProvider>
      <DashboardInner session={session} />
    </ToastProvider>
  )
}
