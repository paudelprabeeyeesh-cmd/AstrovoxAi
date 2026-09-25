import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { editReality, getUniverseMessages } from '../../services/multiverseService'

export default function RealityEditor({ universeId }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('active')
  const [promptVariant, setPromptVariant] = useState('')
  const [modelOverride, setModelOverride] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!universeId) return
    getUniverseMessages(universeId, 10, 0)
      .then((data) => {
        if (data.messages?.length) {
          const last = data.messages[data.messages.length - 1]
          setPromptVariant(last.content?.slice(0, 80) || '')
        }
      })
      .catch(() => {})
  }, [universeId])

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const updates = {
        name: name || undefined,
        description: description || undefined,
        status,
        parameters: {
          ...(promptVariant ? { prompt_variant: promptVariant } : {}),
          ...(modelOverride ? { model_override: modelOverride } : {}),
        },
      }
      const data = await editReality(universeId, updates)
      setMessage(`Universe updated: ${data.universe.name}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '12px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px' }}>
      <h4 style={{ margin: 0, fontSize: '12px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Reality Editor</h4>

      {error && <div style={{ fontSize: '11px', color: '#f87171' }}>⚠️ {error}</div>}
      {message && <div style={{ fontSize: '11px', color: '#34d399' }}>✅ {message}</div>}

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Universe name" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#67e8f9', fontSize: '12px', fontFamily: 'inherit' }} />
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" rows="2" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit', resize: 'vertical' }} />
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#cbd5e1', fontSize: '12px', fontFamily: 'inherit' }}>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="forked">Forked</option>
          <option value="collapsed">Collapsed</option>
        </select>
        <input value={promptVariant} onChange={(e) => setPromptVariant(e.target.value)} placeholder="Prompt variant" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', fontSize: '12px', fontFamily: 'inherit' }} />
        <input value={modelOverride} onChange={(e) => setModelOverride(e.target.value)} placeholder="Model override" style={{ padding: '8px 12px', backgroundColor: '#050a18', border: '1px solid #1e293b', borderRadius: '6px', color: '#94a3b8', fontSize: '12px', fontFamily: 'inherit' }} />
        <button type="submit" disabled={saving || !universeId} style={{ padding: '8px 16px', backgroundColor: '#06b6d4', color: '#02040a', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '700', fontSize: '12px', opacity: saving || !universeId ? 0.5 : 1 }}>
          {saving ? 'Editing Reality...' : 'SAVE REALITY'}
        </button>
      </form>
    </div>
  )
}
