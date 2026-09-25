import { useKnowledgeGraph3D } from '../../hooks/holographic/useKnowledgeGraph3D'
import { HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'

export function KnowledgeGraphExplorer({ className = '', style = {} }) {
  const { nodes, edges, isExplorerActive, startExplorer, stopExplorer, addNode, addEdge, applyLayout } = useKnowledgeGraph3D()

  useEffect(() => {
    if (nodes.length === 0) {
      addNode({
        id: 'ai',
        label: 'Artificial Intelligence',
        type: 'concept',
        x: 0,
        y: 0,
        z: 0
      })
      addNode({
        id: 'nlp',
        label: 'Natural Language Processing',
        type: 'skill',
        x: 1,
        y: 0.5,
        z: -0.5
      })
      addNode({
        id: 'ml',
        label: 'Machine Learning',
        type: 'concept',
        x: -1,
        y: -0.5,
        z: 0.5
      })
      addEdge({ id: 'ai-nlp', source: 'ai', target: 'nlp', type: 'contains' })
      addEdge({ id: 'ai-ml', source: 'ai', target: 'ml', type: 'enables' })
      applyLayout('force_directed')
    }
  }, [])

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        ...style,
        minHeight: '400px'
      }}
    >
      <div style={{
        padding: '16px',
        borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3 style={{
          margin: 0,
          color: HOLOGRAPHIC_COLORS.accent,
          fontSize: '16px',
          fontWeight: 600
        }}>
          Knowledge Graph Explorer
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => applyLayout('force_directed')}
            style={{
              padding: '4px 8px',
              background: 'rgba(6, 182, 212, 0.1)',
              border: `1px solid ${HOLOGRAPHIC_COLORS.primary}40`,
              borderRadius: '4px',
              color: HOLOGRAPHIC_COLORS.accent,
              fontSize: '11px',
              cursor: 'pointer'
            }}
          >
            Force
          </button>
          <button
            onClick={() => applyLayout('circular')}
            style={{
              padding: '4px 8px',
              background: 'rgba(6, 182, 212, 0.1)',
              border: `1px solid ${HOLOGRAPHIC_COLORS.primary}40`,
              borderRadius: '4px',
              color: HOLOGRAPHIC_COLORS.accent,
              fontSize: '11px',
              cursor: 'pointer'
            }}
          >
            Circular
          </button>
          <button
            onClick={isExplorerActive ? stopExplorer : startExplorer}
            style={{
              padding: '4px 8px',
              background: isExplorerActive ? 'rgba(239, 68, 68, 0.1)' : 'rgba(52, 211, 153, 0.1)',
              border: `1px solid ${isExplorerActive ? 'rgba(239, 68, 68, 0.4)' : 'rgba(52, 211, 153, 0.4)'}`,
              borderRadius: '4px',
              color: isExplorerActive ? HOLOGRAPHIC_COLORS.error : HOLOGRAPHIC_COLORS.success,
              fontSize: '11px',
              cursor: 'pointer'
            }}
          >
            {isExplorerActive ? 'Stop' : 'Explore'}
          </button>
        </div>
      </div>
      <div style={{
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        maxHeight: '300px',
        overflowY: 'auto'
      }}>
        {nodes.length === 0 ? (
          <p style={{ color: 'var(--astrovox-text-muted)', fontSize: '13px', textAlign: 'center' }}>
            No nodes in graph. Add nodes to begin exploration.
          </p>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {nodes.map(node => (
                <div
                  key={node.id}
                  style={{
                    padding: '6px 12px',
                    background: 'rgba(6, 182, 212, 0.1)',
                    border: `1px solid ${node.color}40`,
                    borderRadius: '6px',
                    color: node.color,
                    fontSize: '12px'
                  }}
                >
                  {node.label}
                </div>
              ))}
            </div>
            <div style={{ fontSize: '12px', color: 'var(--astrovox-text-muted)' }}>
              Nodes: {nodes.length} | Edges: {edges.length}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
