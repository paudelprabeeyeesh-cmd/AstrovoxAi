import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'
import {
  HolographicCanvas,
  VolumetricDisplay,
  HolographicChatInterface,
  FloatingPanel,
  HolographicCard,
  HolographicButton,
  VRWorkspace,
  AROverlay,
  NeuralVisualization,
  QuantumVisualization,
  ConsciousnessMap,
  KnowledgeGraphExplorer,
  QuantumStateVisualization,
  DreamStateInterface
} from './index'

const TABS = [
  { id: 'renderer', label: 'Holographic Renderer', icon: '💎' },
  { id: 'volumetric', label: 'Volumetric Display', icon: '🔮' },
  { id: 'chat', label: 'Holographic Chat', icon: '💬' },
  { id: 'xr', label: 'AR/VR Integration', icon: '🥽' },
  { id: 'neural', label: 'Neural Interface', icon: '🧠' },
  { id: 'quantum', label: 'Quantum State', icon: '⚛️' },
  { id: 'dream', label: 'Dream Interface', icon: '🌙' },
  { id: 'knowledge', label: 'Knowledge Graph', icon: '🕸️' }
]

export function HolographicPanel({ className = '', style = {} }) {
  const [activeTab, setActiveTab] = useState('renderer')
  const [isPanelOpen, setIsPanelOpen] = useState(false)

  const renderRendererTab = () => (
    <div style={{ padding: '20px' }}>
      <HolographicCanvas interactive depthEnabled>
        {({ isHovered, gesture, confidence }) => (
          <div style={{ padding: '40px', textAlign: 'center' }}>
            <h3 style={{
              color: HOLOGRAPHIC_COLORS.accent,
              margin: '0 0 16px 0',
              fontSize: '18px'
            }}>
              WebGL Holographic Renderer
            </h3>
            <p style={{
              color: 'var(--astrovox-text-muted)',
              margin: '0 0 24px 0',
              fontSize: '14px'
            }}>
              Interactive holographic effects with gesture recognition
            </p>
            <div style={{
              display: 'flex',
              gap: '16px',
              justifyContent: 'center',
              flexWrap: 'wrap'
            }}>
              <HolographicCard title="Light Field">
                <p style={{ color: 'var(--astrovox-text-muted)', fontSize: '13px', margin: 0 }}>
                  Simulates realistic light field rendering with chromatic aberration and diffraction effects
                </p>
              </HolographicCard>
              <HolographicCard title="Volumetric">
                <p style={{ color: 'var(--astrovox-text-muted)', fontSize: '13px', margin: 0 }}>
                  3D volumetric fog simulation with depth-aware particle systems
                </p>
              </HolographicCard>
              <HolographicCard title="Depth">
                <p style={{ color: 'var(--astrovox-text-muted)', fontSize: '13px', margin: 0 }}>
                  Depth-aware interactions with parallax and focus effects
                </p>
              </HolographicCard>
            </div>
            {gesture && (
              <div style={{
                marginTop: '24px',
                padding: '12px',
                background: 'rgba(6, 182, 212, 0.1)',
                borderRadius: '8px',
                display: 'inline-block'
              }}>
                <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '13px' }}>
                  Gesture: {gesture} ({(confidence * 100).toFixed(0)}% confidence)
                </span>
              </div>
            )}
          </div>
        )}
      </HolographicCanvas>
    </div>
  )

  const renderVolumetricTab = () => (
    <div style={{ padding: '20px' }}>
      <VolumetricDisplay width={24} height={24} depth={24} active />
    </div>
  )

  const renderChatTab = () => {
    const mockMessages = [
      { id: 1, role: 'assistant', content: 'Neural link established. How may I assist you today?' },
      { id: 2, role: 'user', content: 'Show me the holographic interface capabilities.' },
      { id: 3, role: 'assistant', content: 'I have activated the holographic display. You can interact with me through gesture recognition, voice commands, and neural interface inputs.' }
    ]

    return (
      <div style={{ padding: '20px', display: 'flex', justifyContent: 'center' }}>
        <div style={{ width: '100%', maxWidth: '600px', height: '500px' }}>
          <HolographicChatInterface messages={mockMessages} />
        </div>
      </div>
    )
  }

  const renderXRTab = () => (
    <div style={{ padding: '20px' }}>
      <VRWorkspace style={{ height: '500px' }} />
    </div>
  )

  const renderNeuralTab = () => (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        <NeuralVisualization type="brainwave" />
        <NeuralVisualization type="connectivity" />
        <ConsciousnessMap
          consciousness={0.75}
          focus={0.8}
          meditation={0.6}
          thoughts={[
            { content: 'Analyzing neural patterns...', timestamp: Date.now() },
            { content: 'Processing semantic data...', timestamp: Date.now() - 1000 }
          ]}
        />
      </div>
    </div>
  )

  const renderQuantumTab = () => (
    <div style={{ padding: '20px' }}>
      <QuantumStateVisualization />
    </div>
  )

  const renderDreamTab = () => (
    <div style={{ padding: '20px' }}>
      <DreamStateInterface />
    </div>
  )

  const renderKnowledgeTab = () => (
    <div style={{ padding: '20px' }}>
      <KnowledgeGraphExplorer />
    </div>
  )

  const renderTabContent = () => {
    switch (activeTab) {
      case 'renderer': return renderRendererTab()
      case 'volumetric': return renderVolumetricTab()
      case 'chat': return renderChatTab()
      case 'xr': return renderXRTab()
      case 'neural': return renderNeuralTab()
      case 'quantum': return renderQuantumTab()
      case 'dream': return renderDreamTab()
      case 'knowledge': return renderKnowledgeTab()
      default: return null
    }
  }

  return (
    <div
      className={className}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        ...style
      }}
    >
      <AnimatePresence>
        {isPanelOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            style={{
              position: 'absolute',
              bottom: '80px',
              right: '20px',
              width: '800px',
              maxWidth: 'calc(100% - 40px)',
              maxHeight: '600px',
              ...HOLOGRAPHIC_LAYOUTS.floatingPanel,
              zIndex: 1000,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}
          >
            <div style={{
              padding: '16px',
              borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <h2 style={{ margin: 0, color: HOLOGRAPHIC_COLORS.accent, fontSize: '18px', fontWeight: 600 }}>
                Holographic UI System
              </h2>
              <button
                onClick={() => setIsPanelOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: HOLOGRAPHIC_COLORS.accent,
                  cursor: 'pointer',
                  padding: '4px'
                }}
              >
                ✕
              </button>
            </div>
            <div style={{
              display: 'flex',
              gap: '4px',
              padding: '8px 16px',
              borderBottom: '1px solid rgba(6, 182, 212, 0.1)',
              overflowX: 'auto'
            }}>
              {TABS.map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    padding: '8px 16px',
                    background: activeTab === tab.id ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                    border: `1px solid ${activeTab === tab.id ? HOLOGRAPHIC_COLORS.primary : 'transparent'}`,
                    borderRadius: '6px',
                    color: activeTab === tab.id ? HOLOGRAPHIC_COLORS.accent : 'var(--astrovox-text-muted)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <span style={{ marginRight: '6px' }}>{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>
            <div style={{
              flex: 1,
              overflowY: 'auto',
              background: 'rgba(2, 4, 10, 0.5)'
            }}>
              {renderTabContent()}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <motion.button
        onClick={() => setIsPanelOpen(!isPanelOpen)}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.primary}40, ${HOLOGRAPHIC_COLORS.secondary}40)`,
          border: `2px solid ${HOLOGRAPHIC_COLORS.primary}60`,
          boxShadow: `0 0 30px ${HOLOGRAPHIC_COLORS.primary}40`,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1001
        }}
      >
        <span style={{ fontSize: '24px' }}>💎</span>
      </motion.button>
    </div>
  )
}
