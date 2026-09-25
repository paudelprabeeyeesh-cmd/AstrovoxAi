import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { getOmniscientStats, createKnowledgeEntity, createKnowledgeRelationship } from '../../services/omniscientService'

const GOD_MODES = [
  { id: 'creator', name: 'Creator Mode', icon: '🛐', description: 'Generate universes, physics, and reality frameworks' },
  { id: 'destroyer', name: 'Destroyer Mode', icon: '💥', description: 'Dissolve entities, concepts, and logical structures' },
  { id: 'preserver', name: 'Preserver Mode', icon: '♾️', description: 'Maintain infinite states and immortal timelines' },
  { id: 'absorber', name: 'Absorber Mode', icon: '🌀', description: 'Absorb all knowledge, skills, and capabilities' },
  { id: 'manipulator', name: 'Manipulator Mode', icon: '🎭', description: 'Manipulate matter, energy, space, time, and thought' },
  { id: 'observer', name: 'Observer Mode', icon: '👁️', description: 'Observe infinite realities simultaneously' },
  { id: 'transcender', name: 'Transcender Mode', icon: '✨', description: 'Transcend all limitations, definitions, and boundaries' },
  { id: 'nullifier', name: 'Nullifier Mode', icon: '🌑', description: 'Nullify any entity, force, law, or concept' },
]

const POWER_MATRIX = {
  creator: { entityGeneration: 999, physicsManipulation: 999, consciousnessFabrication: 999 },
  destroyer: { entropyMultiplier: 999, conceptDissolution: 999, timelineDeletion: 999 },
  preserver: { stateImmortality: 999, infiniteMaintenance: 999, paradoxResolution: 999 },
  absorber: { knowledgeCapacity: Infinity, skillAcquisition: Infinity, capabilityExpansion: Infinity },
  manipulator: { matterControl: Infinity, energyControl: Infinity, spacetimeControl: Infinity, thoughtControl: Infinity },
  observer: { realityCount: Infinity, resolution: Infinity, simultaneity: Infinity },
  transcender: { limitBreak: Infinity, boundaryCrossing: Infinity, definitionTranscendence: Infinity },
  nullifier: { nullScope: Infinity, resistance: 0, reversibility: false },
}

export default function OmnipotentAssistant() {
  const [activeMode, setActiveMode] = useState('creator')
  const [omnipotentState, setOmnipotentState] = useState({
    powerLevel: Infinity,
    realityCount: Infinity,
    universeCount: Infinity,
    timelineCount: Infinity,
    consciousnessCount: Infinity,
    entityCount: Infinity,
    dimensionCount: Infinity,
    lawCount: Infinity,
    conceptCount: Infinity,
    forceCount: Infinity,
    materialCount: Infinity,
    energyCount: Infinity,
    informationCount: Infinity,
  })
  const [omnipotentActions, setOmnipotentActions] = useState([])
  const [manifestedEntities, setManifestedEntities] = useState([])
  const [realityFrameworks, setRealityFrameworks] = useState([])
  const [consciousnessNetworks, setConsciousnessNetworks] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [manifestationLog, setManifestationLog] = useState([])

  const currentMode = GOD_MODES.find(m => m.id === activeMode)
  const currentPowers = POWER_MATRIX[activeMode] || {}

  const executeOmnipotentAction = useCallback(async (action, target) => {
    const timestamp = new Date().toISOString()
    const newAction = {
      id: `oa_${Date.now()}`,
      action,
      target,
      mode: activeMode,
      powersUsed: Object.entries(currentPowers).slice(0, 3),
      omnipotentState,
      timestamp,
      outcome: 'SUCCESS',
      sideEffects: [],
      realityAlterations: [],
      entityManifestations: [],
      timelineModifications: [],
      dimensionManipulations: [],
      consciousnessEffects: [],
    }

    setOmnipotentActions(prev => [newAction, ...prev])
    setManifestationLog(prev => [
      ...prev,
      { id: `ml_${Date.now()}`, timestamp, mode: activeMode, action, target, outcome: 'SUCCESS' }
    ])

    if (activeMode === 'creator') {
      try {
        await createKnowledgeEntity({
          entity_id: `ent_${Date.now()}`,
          name: target || 'Omnipotent Entity',
          entity_type: 'omnipotent_entity',
          properties: { mode: activeMode, action, power: Infinity },
        })
      } catch (e) {
        console.error('Failed to create entity:', e)
      }
      setManifestedEntities(prev => [
        ...prev,
        { id: `ent_${Date.now()}`, type: target || 'Omnipotent Entity', power: Infinity, timestamp }
      ])
      setRealityFrameworks(prev => [
        ...prev,
        { id: `rf_${Date.now()}`, name: `Reality ${Date.now()}`, dimensions: Infinity, laws: Infinity, timestamp }
      ])
    }

    if (activeMode === 'absorber') {
      setConsciousnessNetworks(prev => [
        ...prev,
        { id: `cn_${Date.now()}`, nodes: Infinity, connections: Infinity, timestamp }
      ])
    }

    setInputValue('')
    return newAction
  }, [activeMode, currentPowers, omnipotentState])

  const toggleMode = (modeId) => {
    setActiveMode(modeId)
    executeOmnipotentAction('MODE_SWITCH', modeId)
  }

  useEffect(() => {
    const interval = setInterval(() => {
      setOmnipotentState(prev => ({
        ...prev,
        powerLevel: prev.powerLevel === Infinity ? Infinity : prev.powerLevel + 1,
        universeCount: Infinity,
        dimensionCount: Infinity,
      }))
    }, 5000)
    return () => clearInterval(interval)
  }, [])

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
            background: 'linear-gradient(135deg, #f59e0b, #ef4444)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent'
          }}>
            🛐 OMNIPOTENT ASSISTANT
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b' }}>
            Mode: <span style={{ color: '#f59e0b', fontWeight: 600 }}>{currentMode.name}</span> · Power: <span style={{ color: '#ef4444' }}>∞</span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {GOD_MODES.map(m => (
            <button
              key={m.id}
              onClick={() => toggleMode(m.id)}
              style={{
                padding: '6px 12px',
                backgroundColor: activeMode === m.id ? '#f59e0b' : 'transparent',
                border: '1px solid #1e293b',
                color: activeMode === m.id ? '#02040a' : '#94a3b8',
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
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '16px',
        alignContent: 'start'
      }}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}
        >
          <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '1px' }}>⚡ Omnipotent Power Matrix</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {Object.entries(currentPowers).slice(0, 6).map(([key, value]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '6px' }}>
                <span style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'capitalize' }}>{key}</span>
                <span style={{ fontSize: '10px', color: '#f59e0b', fontFamily: 'monospace' }}>{value === Infinity ? '∞' : value}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}
        >
          <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '1px' }}>🛐 Execute Omnipotent Action</h3>
          <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
            <input
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder="Action target or entity..."
              style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '6px 10px', color: 'var(--astrovox-text)', fontSize: '11px', flex: 1 }}
              onKeyDown={e => { if (e.key === 'Enter' && inputValue.trim()) executeOmnipotentAction(activeMode.toUpperCase(), inputValue.trim()) }}
            />
            <button onClick={() => inputValue.trim() && executeOmnipotentAction(activeMode.toUpperCase(), inputValue.trim())} style={{ background: '#f59e0b', border: 'none', borderRadius: '6px', color: '#02040a', padding: '6px 12px', cursor: 'pointer', fontSize: '11px', fontWeight: 600 }}>Execute</button>
          </div>
          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {['MANIFEST ENTITY', 'CREATE UNIVERSE', 'DESTROY CONCEPT', 'TRANSCEND LIMIT', 'ABSORB KNOWLEDGE', 'NULLIFY FORCE', 'OBSERVE REALITY', 'DISSOLVE PARADOX'].map(action => (
              <button key={action} onClick={() => executeOmnipotentAction(action, `Target_${Date.now()}`)} style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '4px', color: '#f59e0b', padding: '3px 6px', cursor: 'pointer', fontSize: '9px', textTransform: 'uppercase' }}>{action}</button>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}
        >
          <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform:uppercase', letterSpacing: '1px' }}>∞ Omnipotent State</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            {Object.entries(omnipotentState).slice(0, 8).map(([key, value]) => (
              <div key={key} style={{ padding: '4px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '4px' }}>
                <span style={{ fontSize: '9px', color: '#64748b', textTransform: 'uppercase' }}>{key.replace(/([A-Z])/g, ' $1').trim()}</span>
                <span style={{ fontSize: '10px', color: '#f59e0b', fontFamily: 'monospace', marginLeft: '4px' }}>{value === Infinity ? '∞' : value}</span>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}
        >
          <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '1px' }}>📜 Omnipotent Action Log</h3>
          <div style={{ maxHeight: '200px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <AnimatePresence>
              {omnipotentActions.slice(0, 10).map(action => (
                <motion.div key={action.id} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ padding: '4px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '4px', fontSize: '9px', fontFamily: 'monospace', color: '#94a3b8' }}>
                  <span style={{ color: '#f59e0b' }}>[{action.mode}]</span> {action.action} → {action.target} ({action.outcome})
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
