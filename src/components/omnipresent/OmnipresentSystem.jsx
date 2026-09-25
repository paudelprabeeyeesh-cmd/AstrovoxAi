import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import omnipresentService from '../../services/omnipresentService'

const DEVICE_TYPES = [
  { id: 'web', name: 'Web', icon: '🌐' },
  { id: 'mobile', name: 'Mobile', icon: '📱' },
  { id: 'desktop', name: 'Desktop', icon: '🖥️' },
  { id: 'extension', name: 'Extension', icon: '🧩' },
  { id: 'editor', name: 'Editor', icon: '📝' },
  { id: 'wearable', name: 'Wearable', icon: '⌚' },
  { id: 'iot', name: 'IoT', icon: '🏠' },
  { id: 'vehicle', name: 'Vehicle', icon: '🚗' },
]

const ENVIRONMENT_TYPES = [
  { id: 'home', name: 'Home', icon: '🏠' },
  { id: 'work', name: 'Work', icon: '🏢' },
  { id: 'public', name: 'Public', icon: '🌆' },
  { id: 'transit', name: 'Transit', icon: '🚄' },
  { id: 'nature', name: 'Nature', icon: '🌲' },
  { id: 'social', name: 'Social', icon: '👥' },
  { id: 'quiet', name: 'Quiet', icon: '🤫' },
  { id: 'noisy', name: 'Noisy', icon: '📢' },
]

const SOCIAL_PRESENCE_STATES = [
  { id: 'alone', name: 'Alone', icon: '🧘' },
  { id: 'small_group', name: 'Small Group', icon: '👥' },
  { id: 'large_group', name: 'Large Group', icon: '👨‍👩‍👧‍👦' },
  { id: 'one_on_one', name: 'One-on-One', icon: '👤' },
  { id: 'public', name: 'Public', icon: '🌍' },
  { id: 'focused', name: 'Focused', icon: '🎯' },
]

const PROACTIVE_ACTION_TYPES = [
  { id: 'lighting_adjust', name: 'Lighting Adjust', icon: '💡' },
  { id: 'temperature_adjust', name: 'Temperature Adjust', icon: '🌡️' },
  { id: 'notification_suppress', name: 'Notification Suppress', icon: '🔕' },
  { id: 'app_launch', name: 'App Launch', icon: '🚀' },
  { id: 'focus_mode', name: 'Focus Mode', icon: '🎯' },
  { id: 'break_reminder', name: 'Break Reminder', icon: '⏰' },
  { id: 'context_switch', name: 'Context Switch', icon: '🔄' },
]

export default function OmnipresentSystem({ session }) {
  const [activeTab, setActiveTab] = useState('context')
  const [context, setContext] = useState(null)
  const [contextHistory, setContextHistory] = useState([])
  const [devices, setDevices] = useState([])
  const [handoffHistory, setHandoffHistory] = useState([])
  const [socialPresence, setSocialPresence] = useState(null)
  const [collectiveMinds, setCollectiveMinds] = useState([])
  const [sensings, setSensings] = useState({})
  const [proactiveActions, setProactiveActions] = useState([])
  const [environmentalControls, setEnvironmentalControls] = useState({})
  const [timeContext, setTimeContext] = useState(null)
  const [loading, setLoading] = useState(true)
  const [registeringDevice, setRegisteringDevice] = useState(false)
  const intervalRef = useRef(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [ctxRes, historyRes, devicesRes, handoffRes, socialRes, actionsRes, timeRes] = await Promise.all([
        omnipresentService.getAmbientContext(),
        omnipresentService.getContextHistory(20),
        omnipresentService.listDevices(),
        omnipresentService.getHandoffHistory(),
        omnipresentService.getSocialPresence(),
        omnipresentService.getProactiveActions(),
        omnipresentService.getTimeContext(),
      ])

      if (ctxRes?.context) setContext(ctxRes.context)
      if (historyRes?.history) setContextHistory(historyRes.history)
      if (devicesRes?.devices) setDevices(devicesRes.devices)
      if (handoffRes?.history) setHandoffHistory(handoffRes.history)
      if (socialRes?.presence) setSocialPresence(socialRes.presence)
      if (actionsRes?.actions) setProactiveActions(actionsRes.actions)
      if (timeRes?.time_context) setTimeContext(timeRes)
    } catch (err) {
      console.error('Failed to load omnipresent data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (session) {
      loadData()
      intervalRef.current = setInterval(loadData, 8000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [session, loadData])

  const handleRegisterDevice = async (deviceType) => {
    setRegisteringDevice(true)
    try {
      await omnipresentService.registerDevice(deviceType, ['ambient', 'context', 'handoff'])
      await loadData()
    } catch (err) {
      console.error('Failed to register device:', err)
    } finally {
      setRegisteringDevice(false)
    }
  }

  const handleHandoff = async (sourceId, targetId) => {
    try {
      await omnipresentService.initiateHandoff(sourceId, targetId)
      await loadData()
    } catch (err) {
      console.error('Handoff failed:', err)
    }
  }

  const handleSocialPresenceUpdate = async (status) => {
    try {
      await omnipresentService.updateSocialPresence(status)
      await loadData()
    } catch (err) {
      console.error('Failed to update social presence:', err)
    }
  }

  const handleCreateCollectiveMind = async (groupId) => {
    try {
      await omnipresentService.createCollectiveMind(groupId, [session?.user?.email || 'user'])
      await loadData()
    } catch (err) {
      console.error('Failed to create collective mind:', err)
    }
  }

  const handlePredictAction = async () => {
    try {
      await omnipresentService.predictProactiveAction()
      await loadData()
    } catch (err) {
      console.error('Failed to predict action:', err)
    }
  }

  const handleEnvironmentalControl = async (deviceId, controlType, value, unit = '') => {
    try {
      await omnipresentService.applyEnvironmentalControl(deviceId, controlType, value, unit)
      await loadData()
    } catch (err) {
      console.error('Failed to apply control:', err)
    }
  }

  const getTimeBasedSuggestion = () => {
    if (!timeContext) return 'Adapting to your environment...'
    const hour = new Date().getHours()
    if (hour >= 5 && hour < 9) return '🌅 Morning optimization active'
    if (hour >= 9 && hour < 12) return '☀️ Focus mode recommended'
    if (hour >= 12 && hour < 14) return '🌤️ Post-lunch awareness'
    if (hour >= 14 && hour < 17) return '🌇 Afternoon deep work'
    if (hour >= 17 && hour < 21) return '🌃 Evening ambient mode'
    if (hour >= 21 || hour < 5) return '🌙 Night wind-down active'
    return 'Adapting to your environment...'
  }

  const tabs = [
    { id: 'context', name: 'Context', icon: '🧠' },
    { id: 'devices', name: 'Devices', icon: '📱' },
    { id: 'social', name: 'Social', icon: '👥' },
    { id: 'collective', name: 'Collective', icon: '🔮' },
    { id: 'ambient', name: 'Ambient', icon: '🌐' },
    { id: 'assistance', name: 'Assistance', icon: '🤖' },
    { id: 'environment', name: 'Environment', icon: '🏠' },
  ]

  if (loading && !context) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#02040a',
        color: '#06b6d4',
        fontFamily: 'monospace'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            display: 'inline-block',
            width: '40px',
            height: '40px',
            border: '3px solid #06b6d4',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            marginBottom: '20px'
          }} />
          <p>🌐 SYNCHRONIZING OMNIPRESENCE...</p>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    )
  }

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
            background: 'linear-gradient(135deg, #06b6d4, #a78bfa)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            color: 'transparent'
          }}>
            🌐 OMNIPRESENT SYSTEM
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '10px', color: '#64748b' }}>
            {getTimeBasedSuggestion()}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '6px 12px',
                backgroundColor: activeTab === tab.id ? '#06b6d4' : 'transparent',
                border: '1px solid #1e293b',
                color: activeTab === tab.id ? '#02040a' : '#94a3b8',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '11px',
                fontWeight: '600',
                transition: 'all 0.2s',
                whiteSpace: 'nowrap'
              }}
            >
              {tab.icon} {tab.name}
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
        {activeTab === 'context' && (
          <>
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '1px' }}>🧠 Current Ambient Context</h3>
              {context && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <ContextRow label="Environment" value={context.environment} />
                  <ContextRow label="Time Context" value={context.time_context} />
                  <ContextRow label="Social Presence" value={context.social_presence} />
                  <ContextRow label="Device Type" value={context.device_type} />
                  <ContextRow label="Presence Mode" value={context.presence_mode} />
                  <ContextRow label="Activity" value={context.activity_type} />
                  <ContextRow label="Attention" value={context.attention_focus} />
                  <ContextRow label="Connectivity" value={context.connectivity} />
                  <ContextRow label="Light Level" value={`${(context.ambient_light_level * 100).toFixed(0)}%`} />
                  <ContextRow label="Noise Level" value={`${(context.noise_level * 100).toFixed(0)}%`} />
                  {context.battery_level && <ContextRow label="Battery" value={`${(context.battery_level * 100).toFixed(0)}%`} />}
                </div>
              )}
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '1px' }}>📜 Context History</h3>
              <div style={{ maxHeight: '300px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                <AnimatePresence>
                  {contextHistory.slice(0, 10).map(ctx => (
                    <motion.div key={ctx.context_id} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} style={{ padding: '6px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '4px', fontSize: '10px', fontFamily: 'monospace', color: '#94a3b8' }}>
                      <span style={{ color: '#06b6d4' }}>[{new Date(ctx.timestamp * 1000).toLocaleTimeString()}]</span> {ctx.environment} · {ctx.activity_type}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </motion.div>
          </>
        )}

        {activeTab === 'devices' && (
          <>
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '1px' }}>📱 Register Device</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {DEVICE_TYPES.map(dt => (
                  <button key={dt.id} onClick={() => handleRegisterDevice(dt.id)} disabled={registeringDevice} style={{ background: 'rgba(6,182,212,0.1)', border: '1px solid rgba(6,182,212,0.2)', borderRadius: '6px', color: '#06b6d4', padding: '8px 12px', cursor: 'pointer', fontSize: '11px', textTransform: 'uppercase', fontWeight: 600 }}>
                    {dt.icon} {dt.name}
                  </button>
                ))}
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '1px' }}>🔄 Multi-Device Handoff</h3>
              {devices.length >= 2 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {devices.slice(0, 4).map((d, i) => devices.slice(i + 1, i + 2).map(d2 => (
                    <button key={`${d.device_id}-${d2.device_id}`} onClick={() => handleHandoff(d.device_id, d2.device_id)} style={{ background: 'rgba(6,182,212,0.1)', border: '1px solid rgba(6,182,212,0.2)', borderRadius: '6px', color: '#06b6d4', padding: '8px 12px', cursor: 'pointer', fontSize: '11px', textTransform: 'uppercase', fontWeight: 600 }}>
                      {d.device_type} → {d2.device_type}
                    </button>
                  )))}
                </div>
              ) : (
                <p style={{ fontSize: '11px', color: '#64748b' }}>Register at least 2 devices to enable handoff.</p>
              )}
              {handoffHistory.length > 0 && (
                <div style={{ marginTop: '12px', maxHeight: '150px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  {handoffHistory.slice(0, 5).map(h => (
                    <div key={h.session_id} style={{ padding: '4px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '4px', fontSize: '9px', fontFamily: 'monospace', color: '#94a3b8' }}>
                      <span style={{ color: '#06b6d4' }}>[{h.status}]</span> {h.source_device_id} → {h.target_device_id}
                    </div>
                  ))}
                </div>
              )}
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '1px' }}>📋 Registered Devices</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {devices.map(d => (
                  <div key={d.device_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '10px', color: '#94a3b8' }}>{d.device_type}</span>
                    <span style={{ fontSize: '9px', color: d.is_active ? '#34d399' : '#ef4444', fontFamily: 'monospace' }}>{d.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
                  </div>
                ))}
                {devices.length === 0 && <p style={{ fontSize: '10px', color: '#64748b' }}>No devices registered yet.</p>}
              </div>
            </motion.div>
          </>
        )}

        {activeTab === 'social' && (
          <>
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '1px' }}>👥 Social Presence Indicators</h3>
              {socialPresence && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <StatusRow label="Current Status" value={socialPresence.status} color="#a78bfa" />
                  <div style={{ marginTop: '8px' }}>
                    <span style={{ fontSize: '10px', color: '#64748b', textTransform: 'uppercase' }}>Update Status</span>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '6px' }}>
                      {SOCIAL_PRESENCE_STATES.map(sp => (
                        <button key={sp.id} onClick={() => handleSocialPresenceUpdate(sp.id)} style={{ background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', borderRadius: '4px', color: '#a78bfa', padding: '4px 8px', cursor: 'pointer', fontSize: '9px', textTransform: 'uppercase', fontWeight: 600 }}>
                          {sp.icon} {sp.name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '1px' }}>🧠 Collaborative Telepathy</h3>
              <p style={{ fontSize: '10px', color: '#64748b', margin: '0 0 8px 0' }}>Share thoughts directly with nearby users via neural link simulation.</p>
              <div style={{ display: 'flex', gap: '6px' }}>
                <button onClick={() => handleCreateCollectiveMind(`group_${Date.now()}`)} style={{ background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)', borderRadius: '6px', color: '#a78bfa', padding: '8px 12px', cursor: 'pointer', fontSize: '11px', fontWeight: 600 }}>
                  Create Telepathic Link
                </button>
              </div>
            </motion.div>
          </>
        )}

        {activeTab === 'collective' && (
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px', gridColumn: '1 / -1' }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#a78bfa', textTransform: 'uppercase', letterSpacing: '1px' }}>🔮 Group Mind Interface & Collective Intelligence</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
              <CollectiveMindCard />
              <div style={{ background: 'rgba(6,182,212,0.05)', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '11px', color: '#06b6d4', textTransform: 'uppercase' }}>Emergent Insights</h4>
                {collectiveMinds.length === 0 ? (
                  <p style={{ fontSize: '10px', color: '#64748b' }}>Create a collective mind to see emergent insights.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {collectiveMinds.slice(0, 3).flatMap(m => m.emergent_insights).map((insight, i) => (
                      <div key={i} style={{ padding: '4px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '4px', fontSize: '9px', color: '#94a3b8' }}>{insight}</div>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ background: 'rgba(6,182,212,0.05)', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px' }}>
                <h4 style={{ margin: '0 0 8px', fontSize: '11px', color: '#06b6d4', textTransform: 'uppercase' }}>Shared Thoughts</h4>
                {collectiveMinds.length === 0 ? (
                  <p style={{ fontSize: '10px', color: '#64748b' }}>No shared thoughts yet.</p>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {collectiveMinds.slice(0, 3).flatMap(m => m.shared_thoughts.slice(0, 2)).map((thought, i) => (
                      <div key={i} style={{ padding: '4px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '4px', fontSize: '9px', color: '#94a3b8' }}>{JSON.stringify(thought)}</div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'ambient' && (
          <>
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '1px' }}>🌐 Ambient Sensing & Response</h3>
              <p style={{ fontSize: '10px', color: '#64748b', margin: '0 0 8px 0' }}>Simulated ambient sensors monitoring your environment.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {['proximity', 'light', 'sound', 'motion', 'temperature'].map(sensor => (
                  <div key={sensor} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(245,158,11,0.05)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'capitalize' }}>{sensor}</span>
                    <span style={{ fontSize: '10px', color: '#f59e0b', fontFamily: 'monospace' }}>{Math.random().toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '1px' }}>🌍 Ubiquitous Computing Integration</h3>
              <p style={{ fontSize: '10px', color: '#64748b', margin: '0 0 8px 0' }}>AI presence synchronized across all computing surfaces.</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {devices.map(d => (
                  <div key={d.device_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(245,158,11,0.05)', borderRadius: '6px' }}>
                    <span style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'capitalize' }}>{d.device_type}</span>
                    <span style={{ fontSize: '9px', color: d.is_active ? '#34d399' : '#ef4444', fontFamily: 'monospace' }}>{d.is_active ? 'CONNECTED' : 'OFFLINE'}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          </>
        )}

        {activeTab === 'assistance' && (
          <>
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '1px' }}>🤖 Proactive Assistance</h3>
              <div style={{ display: 'flex', gap: '6px', marginBottom: '8px', flexWrap: 'wrap' }}>
                {PROACTIVE_ACTION_TYPES.map(action => (
                  <button key={action.id} onClick={() => handleEnvironmentalControl('all', action.id, true)} style={{ background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '4px', color: '#f59e0b', padding: '4px 8px', cursor: 'pointer', fontSize: '9px', textTransform: 'uppercase', fontWeight: 600 }}>
                    {action.icon} {action.name}
                  </button>
                ))}
              </div>
              {proactiveActions.length > 0 && (
                <div style={{ maxHeight: '200px', overflow: 'auto', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  {proactiveActions.slice(0, 8).map(action => (
                    <div key={action.action_id} style={{ padding: '4px 8px', background: 'rgba(245,158,11,0.05)', borderRadius: '4px', fontSize: '9px', fontFamily: 'monospace', color: '#94a3b8' }}>
                      <span style={{ color: '#f59e0b' }}>[{action.confidence > 0.8 ? 'HIGH' : 'MED'}]</span> {action.action_type} → {action.predicted_need}
                    </div>
                  ))}
                </div>
              )}
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#f59e0b', textTransform: 'uppercase', letterSpacing: '1px' }}>🔮 Predict Next Action</h3>
              <button onClick={handlePredictAction} style={{ background: '#f59e0b', border: 'none', borderRadius: '6px', color: '#02040a', padding: '10px 16px', cursor: 'pointer', fontSize: '12px', fontWeight: 600, width: '100%' }}>
                Predict Proactive Action
              </button>
            </motion.div>
          </>
        )}

        {activeTab === 'environment' && (
          <>
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px', gridColumn: '1 / -1' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#34d399', textTransform: 'uppercase', letterSpacing: '1px' }}>🏠 Environmental Controls</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                <EnvControlCard
                  title="Lighting"
                  icon="💡"
                  controlType="lighting"
                  deviceId={devices[0]?.device_id || 'default'}
                  onApply={handleEnvironmentalControl}
                  min={0} max={100} unit="%"
                />
                <EnvControlCard
                  title="Temperature"
                  icon="🌡️"
                  controlType="temperature"
                  deviceId={devices[0]?.device_id || 'default'}
                  onApply={handleEnvironmentalControl}
                  min={16} max={30} unit="°C"
                />
                <EnvControlCard
                  title="Humidity"
                  icon="💧"
                  controlType="humidity"
                  deviceId={devices[0]?.device_id || 'default'}
                  onApply={handleEnvironmentalControl}
                  min={30} max={70} unit="%"
                />
                <EnvControlCard
                  title="Sound"
                  icon="🔊"
                  controlType="sound"
                  deviceId={devices[0]?.device_id || 'default'}
                  onApply={handleEnvironmentalControl}
                  min={0} max={100} unit="%"
                />
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} style={{ background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '12px', padding: '16px', gridColumn: '1 / -1' }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '13px', color: '#34d399', textTransform: 'uppercase', letterSpacing: '1px' }}>📍 Location-Aware Features</h3>
              {context?.location && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <ContextRow label="Latitude" value={context.location.lat?.toFixed(4)} />
                  <ContextRow label="Longitude" value={context.location.lon?.toFixed(4)} />
                  <ContextRow label="Accuracy" value={`${context.location.accuracy_m?.toFixed(0)}m`} />
                </div>
              )}
              {!context?.location && <p style={{ fontSize: '10px', color: '#64748b' }}>Location data will appear here when available.</p>}
            </motion.div>
          </>
        )}
      </div>
    </div>
  )
}

function ContextRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '6px' }}>
      <span style={{ fontSize: '9px', color: '#64748b', textTransform: 'uppercase' }}>{label}</span>
      <span style={{ fontSize: '10px', color: '#06b6d4', fontFamily: 'monospace', textTransform: 'capitalize' }}>{value}</span>
    </div>
  )
}

function StatusRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 8px', background: 'rgba(6,182,212,0.05)', borderRadius: '6px' }}>
      <span style={{ fontSize: '9px', color: '#64748b', textTransform: 'uppercase' }}>{label}</span>
      <span style={{ fontSize: '10px', color, fontFamily: 'monospace', textTransform: 'capitalize', fontWeight: 600 }}>{value}</span>
    </div>
  )
}

function CollectiveMindCard() {
  const [mindId, setMindId] = useState('')
  const [participants, setParticipants] = useState('')

  const handleCreate = async () => {
    if (!mindId) return
    try {
      const { createCollectiveMind } = await import('../../services/omnipresentService')
      await createCollectiveMind(mindId, participants.split(',').map(p => p.trim()).filter(Boolean))
      setMindId('')
      setParticipants('')
    } catch (err) {
      console.error('Failed to create mind:', err)
    }
  }

  return (
    <div style={{ background: 'rgba(6,182,212,0.05)', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px' }}>
      <h4 style={{ margin: '0 0 8px', fontSize: '11px', color: '#a78bfa', textTransform: 'uppercase' }}>Create Collective Mind</h4>
      <input
        value={mindId}
        onChange={e => setMindId(e.target.value)}
        placeholder="Group ID"
        style={{ width: '100%', padding: '6px 8px', marginBottom: '6px', background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '4px', color: '#e2e8f0', fontSize: '10px' }}
      />
      <input
        value={participants}
        onChange={e => setParticipants(e.target.value)}
        placeholder="Participants (comma-separated)"
        style={{ width: '100%', padding: '6px 8px', marginBottom: '8px', background: 'rgba(4,8,20,0.6)', border: '1px solid #1e293b', borderRadius: '4px', color: '#e2e8f0', fontSize: '10px' }}
      />
      <button onClick={handleCreate} style={{ background: 'rgba(167,139,250,0.2)', border: '1px solid rgba(167,139,250,0.3)', borderRadius: '6px', color: '#a78bfa', padding: '8px 12px', cursor: 'pointer', fontSize: '11px', fontWeight: 600, width: '100%' }}>
        Initialize Mind
      </button>
    </div>
  )
}

function EnvControlCard({ title, icon, controlType, deviceId, onApply, min, max, unit }) {
  const [value, setValue] = useState(min + Math.floor((max - min) / 2))

  return (
    <div style={{ background: 'rgba(6,182,212,0.05)', border: '1px solid #1e293b', borderRadius: '8px', padding: '12px' }}>
      <h4 style={{ margin: '0 0 8px', fontSize: '11px', color: '#34d399', textTransform: 'uppercase' }}>
        {icon} {title}
      </h4>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
        <input
          type="range"
          min={min}
          max={max}
          value={value}
          onChange={e => setValue(Number(e.target.value))}
          style={{ flex: 1, accentColor: '#34d399' }}
        />
        <span style={{ fontSize: '10px', color: '#34d399', fontFamily: 'monospace', minWidth: '40px', textAlign: 'right' }}>{value}{unit}</span>
      </div>
      <button onClick={() => onApply(deviceId, controlType, value, unit)} style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.2)', borderRadius: '4px', color: '#34d399', padding: '6px 10px', cursor: 'pointer', fontSize: '10px', fontWeight: 600, width: '100%' }}>
        Apply {title}
      </button>
    </div>
  )
}
