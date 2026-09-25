import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import WebGLHolographicChat from './WebGLHolographicChat'
import VolumetricUIPanel from './VolumetricUIPanel'
import QuantumCircuitSimulator from './QuantumCircuitSimulator'
import QuantumStateVisualizer from './QuantumStateVisualizer'
import LightFieldRenderer from './LightFieldRenderer'
import HolographicAssistantAvatar from './HolographicAssistantAvatar'
import QuantumBenchmarkDashboard from './QuantumBenchmarkDashboard'
import QKDProtocol from './QKDProtocol'
import QuantumRandomTheme from './QuantumRandomTheme'
import HolographicGestureControls from './HolographicGestureControls'

const modules = [
  { id: 'circuit', name: 'Quantum Circuit', component: QuantumCircuitSimulator, icon: '⚛️' },
  { id: 'state', name: 'State Visualizer', component: QuantumStateVisualizer, icon: '🔮' },
  { id: 'benchmark', name: 'Benchmark', component: QuantumBenchmarkDashboard, icon: '📊' },
  { id: 'qkd', name: 'QKD Protocol', component: QKDProtocol, icon: '🔐' },
  { id: 'theme', name: 'Quantum Theme', component: QuantumRandomTheme, icon: '🎲' },
  { id: 'avatar', name: 'Holo Avatar', component: HolographicAssistantAvatar, icon: '🛸' },
  { id: 'light', name: 'Light Field', component: LightFieldRenderer, icon: '💡' },
  { id: 'gesture', name: 'Gestures', component: HolographicGestureControls, icon: '🖐️' },
  { id: 'chat', name: 'Holo Chat', component: WebGLHolographicChat, icon: '🌐' },
  { id: 'volumetric', name: 'Volumetric', component: VolumetricUIPanel, icon: '📦' }
]

export default function QuantumHolographicSystem() {
  const [activeModule, setActiveModule] = useState('circuit')
  const [activeModules, setActiveModules] = useState(['circuit'])

  const toggleModule = (id) => {
    setActiveModules(prev =>
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    )
    setActiveModule(id)
  }

  const ActiveComponent = modules.find(m => m.id === activeModule)?.component

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: '#02040a',
      color: '#e2e8f0',
      fontFamily: "'Inter', 'Segoe UI', monospace",
      backgroundImage: 'radial-gradient(ellipse at 50% 0%, rgba(6, 182, 212, 0.05) 0%, transparent 70%)'
    }}>
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
            ⚛️ QUANTUM HOLOGRAPHIC COMPUTING
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b' }}>
            {activeModules.length} module{activeModules.length !== 1 ? 's' : ''} active · Quantum state coherence: 99.7%
          </p>
        </div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {modules.map(m => (
            <button
              key={m.id}
              onClick={() => toggleModule(m.id)}
              style={{
                padding: '6px 12px',
                backgroundColor: activeModules.includes(m.id) ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activeModules.includes(m.id) ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s',
                whiteSpace: 'nowrap'
              }}
            >
              {m.icon} {m.name}
            </button>
          ))}
        </div>
      </header>

      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '16px',
        display: 'grid',
        gridTemplateColumns: activeModules.length > 1 ? 'repeat(auto-fit, minmax(400px, 1fr))' : '1fr',
        gap: '16px',
        alignContent: 'start'
      }}>
        <AnimatePresence>
          {activeModules.map(id => {
            const mod = modules.find(m => m.id === id)
            if (!mod) return null
            const Component = mod.component
            return (
              <motion.div
                key={id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3 }}
              >
                <Component />
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>

      <div style={{
        paddingTop: '16px',
        borderTop: '1px solid #1e293b',
        textAlign: 'center',
        fontSize: '10px',
        color: '#475569',
        letterSpacing: '0.5px',
        padding: '16px'
      }}>
        QUANTUM HOLOGRAPHIC COMPUTING INTERFACE v1.0.0 · Quantum coherence maintained
      </div>
    </div>
  )
}
