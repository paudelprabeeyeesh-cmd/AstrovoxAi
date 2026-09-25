import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { memoryPalaceRegister, memoryPalaceNavigate, memoryPalaceCurrent } from '../../services/neuralService'

const NEURAL_COLORS = {
  primary: '#06b6d4',
  secondary: '#8b5cf6',
  accent: '#22d3ee',
  cardBackground: 'rgba(6, 182, 212, 0.08)',
  border: 'rgba(6, 182, 212, 0.25)',
  text: '#e5e7eb',
  muted: '#9ca3af',
}

export function MemoryPalace({ className = '', style = {} }) {
  const [palaceId, setPalaceId] = useState('')
  const [nodes, setNodes] = useState([])
  const [currentNode, setCurrentNode] = useState(null)
  const [palace, setPalace] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    memoryPalaceCurrent().then((res) => {
      if (res.palace) setPalace(res.palace)
    }).catch(() => {})
  }, [])

  const handleRegister = useCallback(async () => {
    if (!nodes.length) return
    setLoading(true)
    setError(null)
    try {
      const res = await memoryPalaceRegister(palaceId, nodes)
      setPalaceId(res.palace_id)
      setPalace(nodes.map((n) => ({ node_id: n.node_id, label: n.label, position: n.position, tags: n.tags })))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [palaceId, nodes])

  const handleNavigate = useCallback(async (nodeId) => {
    if (!palaceId) return
    setLoading(true)
    setError(null)
    try {
      const res = await memoryPalaceNavigate(palaceId, nodeId)
      setCurrentNode(res.node)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [palaceId])

  const addNode = useCallback(() => {
    setNodes((prev) => [
      ...prev,
      { node_id: `node_${Date.now()}`, label: `Memory ${prev.length + 1}`, position: [0, 0, 0], tags: [], memory_store: {}, metadata: {} },
    ])
  }, [])

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: NEURAL_COLORS.cardBackground,
        border: `1px solid ${NEURAL_COLORS.border}`,
        borderRadius: '16px',
        padding: '24px',
        backdropFilter: 'blur(12px)',
        ...style,
      }}
    >
      <h3 style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.accent, fontSize: '18px', fontWeight: 600 }}>
        Memory Palace Navigation
      </h3>
      <p style={{ margin: '0 0 16px 0', color: NEURAL_COLORS.muted, fontSize: '13px' }}>
        Navigate memory structures via spatial indexing.
      </p>

      <div style={{ marginBottom: '12px', display: 'flex', gap: '8px' }}>
        <input
          value={palaceId}
          onChange={(e) => setPalaceId(e.target.value)}
          placeholder="Palace ID"
          style={{
            flex: 1,
            background: 'rgba(0,0,0,0.3)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '13px',
          }}
        />
        <button
          onClick={addNode}
          style={{
            background: `${NEURAL_COLORS.secondary}20`,
            border: `1px solid ${NEURAL_COLORS.secondary}40`,
            borderRadius: '8px',
            padding: '8px 12px',
            color: NEURAL_COLORS.text,
            fontSize: '12px',
            cursor: 'pointer',
          }}
        >
          Add Node
        </button>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>
          Nodes ({nodes.length})
        </div>
        <div style={{ maxHeight: '120px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {nodes.map((node, i) => (
            <div
              key={node.node_id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'rgba(0,0,0,0.2)',
                border: `1px solid ${NEURAL_COLORS.border}`,
                borderRadius: '6px',
                padding: '6px 10px',
              }}
            >
              <span style={{ color: NEURAL_COLORS.text, fontSize: '12px' }}>{node.label}</span>
              <button
                onClick={() => handleNavigate(node.node_id)}
                style={{
                  background: `${NEURAL_COLORS.primary}20`,
                  border: `1px solid ${NEURAL_COLORS.primary}40`,
                  borderRadius: '4px',
                  padding: '2px 8px',
                  color: NEURAL_COLORS.accent,
                  fontSize: '11px',
                  cursor: 'pointer',
                }}
              >
                Navigate
              </button>
            </div>
          ))}
          {nodes.length === 0 && (
            <div style={{ color: NEURAL_COLORS.muted, fontSize: '12px' }}>No nodes yet.</div>
          )}
        </div>
      </div>

      <button
        onClick={handleRegister}
        disabled={loading || !nodes.length}
        style={{
          background: `linear-gradient(135deg, ${NEURAL_COLORS.primary}40, ${NEURAL_COLORS.primary}20)`,
          border: `1px solid ${NEURAL_COLORS.primary}60`,
          borderRadius: '8px',
          padding: '8px 16px',
          color: NEURAL_COLORS.accent,
          fontSize: '13px',
          fontWeight: 500,
          cursor: loading || !nodes.length ? 'not-allowed' : 'pointer',
          opacity: loading || !nodes.length ? 0.6 : 1,
          marginBottom: '16px',
        }}
      >
        {loading ? 'Registering...' : 'Register Palace'}
      </button>

      {error && (
        <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '12px' }}>
          {error}
        </div>
      )}

      {currentNode && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{
            background: 'rgba(0,0,0,0.25)',
            border: `1px solid ${NEURAL_COLORS.border}`,
            borderRadius: '12px',
            padding: '16px',
          }}
        >
          <div style={{ color: NEURAL_COLORS.muted, fontSize: '11px', marginBottom: '6px' }}>
            Current Node
          </div>
          <div style={{ color: NEURAL_COLORS.text, fontSize: '14px', fontWeight: 600, marginBottom: '8px' }}>
            {currentNode.label}
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {currentNode.tags?.map((tag, i) => (
              <span
                key={i}
                style={{
                  background: `${NEURAL_COLORS.primary}20`,
                  border: `1px solid ${NEURAL_COLORS.primary}40`,
                  borderRadius: '999px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  color: NEURAL_COLORS.accent,
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
