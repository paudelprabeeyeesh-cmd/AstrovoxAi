import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from ' 'framer-motion'
import Icon from '../../design/Iconography'

export default function CausalChain({ events, onEventClick }) {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [filter, setFilter] = useState('all')
  const [highlightRoot, setHighlightRoot] = useState(true)
  const [highlightLeaf, setHighlightLeaf] = useState(true)
  const [analysis, setAnalysis] = useState(null)
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [viewMode, setViewMode] = useState('graph')
  const [eventDetail, setEventDetail] = useState(null)
  const [rootCauses, setRootCauses] = useState([])
  const [downstreamEvents, setDownstreamEvents] = useState([])
  const [upstreamEvents, setUpstreamEvents] = useState([])

  const [upstream, setUpstream] = useState([])
  const [downstream, setDownstream] = useState([])
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [eventImpact, setEventImpact] = useState(null)

  useEffect(() => {
    if (events && events.length > 0) {
      const nodesData = events.map((event, index) => ({
        id: event.event_id || `evt_${index}`,
        label: event.event_type,
        subLabel: event.aggregate_id,
        timestamp: event.occurred_at || new Date().toISOString(),
        data: event,
        type: event.event_type,
        impact: event.impact || 'medium',
        x: (index % 5) * 120 + 50,
        y: Math.floor(index / 5) * 60 + 50,
      }))
      const edgesData = []
      for (let i = 0; i < events.length - 1; i++) {
        edgesData.push({
          source: events[i].event_id || `evt_${i}`,
          target: events[i + 1].event_id || `evt_${i + 1}`,
          type: 'preceded',
          weight: 1.0,
          confidence: 1.0,
        })
      }
      setNodes(nodesData)
      setEdges(edgesData)
      setGraphData({ nodes: nodesData, edges: edgesData })
    }
  }, [events])

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node)
    setSelectedEvent(node)
    setEventDetail(node.data)
    const upstream = nodes.filter(n => edges.some(e => e.target === node.id && e.source === n.id))
    setDownstream(nodes.filter(n => edges.some(e => e.source === node.id && e.target === n.id)))
    setUpstream(upstream)
    setEventImpact({
      upstream_count: upstream.length,
      downstream_count: nodes.filter(n => edges.some(e => e.source === node.id && e.target === n.id)).length,
      total_reach: 1 + upstream.length + nodes.filter(n => edges.some(e => e.source === node.id && e.target === n.id)).length,
    })
    onEventClick?.(node.data)
  }, [nodes, edges, onEventClick])

  const analyzeCausalChain = useCallback(() => {
    const rootCauses = nodes.filter(node => !edges.some(e => e.target === node.id))
    const leaves = nodes.filter(node => !edges.some(e => e.source === node.id))
    const upstreamList = selectedNode ? nodes.filter(n => edges.some(e => e.target === selectedNode.id && e.source === n.id)) : []
    const downstreamList = selectedNode ? nodes.filter(n => edges.some(e => e.source === selectedNode.id && e.target === n.id)) : []
    setAnalysis({
      root_causes: rootCauses,
      leaves: leaves,
      upstream: upstreamList,
      downstream: downstreamList,
    })
    setRootCauses(rootCauses)
    setUpstreamEvents(upstreamList)
    setDownstreamEvents(downstreamList)
  }, [nodes, edges, selectedNode])

  const getImpactColor = (impact) => {
    if (impact === 'high') return 'var(--astrovox-error)'
    if (impact === 'medium') return 'var(--astrovox-warning)'
    return 'var(--astrovox-text-muted)'
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '4px' }}>
        <select value={viewMode} onChange={e => setViewMode(e.target.value)} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', fontSize: '11px', padding: '2px 4px' }}>
          <option value="graph">Graph View</option>
          <option value="list">ListView</option>
          <option value="detail">Detail View</option>
        </select>
        <select value={filter} onChange={e => setFilter(e.target.value)} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', fontSize: '11px', padding: '2px 4px' }}>
          <option value="all">All</option>
          <option value="root">Root Causes</option>
          <option value="leaf">Leaf Events</option>
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--astrovox-text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={highlightRoot} onChange={e => setHighlightRoot(e.target.checked)} /> Root
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: 'var(--astrovox-text-muted)', cursor: 'pointer' }}>
          <input type="checkbox" checked={highlightLeaf} onChange={e => setHighlightLeaf(e.target.checked)} /> Leaf
        </label>
        <button onClick={analyzeCausalChain} style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', color: 'var(--astrovox-text)', padding: '4px 8px', cursor: 'pointer', fontSize: '10px' }}>Analyze</button>
      </div>

      <div style={{ flex: 1, display: 'flex', gap: '8px', overflow: 'hidden' }}>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'auto' }}>
          {viewMode === 'graph' && (
            <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', position: 'relative', minHeight: '300px', overflow: 'auto' }}>
              <div style={{ position: 'relative', height: '100%', minWidth: '500px' }}>
                {edges.map((edge, index) => {
                  const source = nodes.find(n => n.id === edge.source)
                  const target = nodes.find(n => n.id === edge.target)
                  if (!source || !target) return null
                  const midX = (source.x + target.x) / 2
                  const midY = (source.y + target.y) / 2
                  return (
                    <div key={edge.source} style={{ position: 'absolute', left: `${midX}px`, top: `${midY}px`, width: `${Math.abs(target.x - source.x)}px`, height: '2px', background: 'var(--astrovox-border)', transform: `rotate(${Math.atan2(target.y - source.y, target.x - source.x)}rad)`, transformOrigin: 'top left' }} />
                  )
                })}
                {nodes.map((node, index) => (
                  <div key={node.id} onClick={() => handleNodeClick(node)} style={{ position: 'absolute', left: `${node.x}px`, top: `${node.y}px', padding: '6px 10px', borderRadius: 'var(--astrovox-radius)', cursor: 'pointer', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: selectedNode?.id === node.id ? 'var(--astrovox-surface-hover)' : 'var(--astrovox-surface)', border: `1px solid ${selectedNode?.id === node.id ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`, display: 'flex', alignItems: 'center', gap: '6px', zIndex: 1 }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: getImpactColor(node.impact) }} />
                    <span>{node.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {viewMode === 'list' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', overflow: 'auto', maxHeight: '300px' }}>
              {nodes.map((node, index) => (
                <div key={node.id} onClick={() => handleNodeClick(node)} style={{ padding: '6px 10px', borderRadius: 'var(--astrovox-radius)', cursor: 'pointer', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', background: selectedNode?.id === node.id ? 'var(--astrovox-surface-hover)' : 'var(--astrovox-surface)', border: `1px solid ${selectedNode?.id === node.id ? 'var(--astrovox-primary)' : 'var(--astrovox-border)'}`, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: getImpactColor(node.impact) }} />
                  <span>{node.label}</span>
                  <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '9px' }}>{node.timestamp}</span>
                </div>
              ))}
            </div>
          )}
          {viewMode === 'detail' && eventDetail && (
            <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', overflow: 'auto' }}>
              <pre style={{ background: 'var(--astrovox-bg)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px', fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)', whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(eventDetail, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div style={{ width: '300px', display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'auto' }}>
          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Selected Event</h3>
            {eventDetail ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>{eventDetail.event_type}</span>
                <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>{eventDetail.aggregate_id}</span>
                <span style={{ fontSize: '9px', color: 'var(--astrovox-text-muted)', fontFamily: 'monospace' }}>{formatTimestamp(eventDetail.occurred_at)}</span>
              </div>
            ) : (
              <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>No event selected</span>
            )}
          </div>

          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Impact</h3>
            {eventImpact ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>Upstream: {eventImpact.upstream_count}</span>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>Downstream: {eventImpact.downstream_count}</span>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>Total Reach: {eventImpact.total_reach}</span>
              </div>
            ) : (
              <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Select an event to analyze</span>
            )}
          </div>

          <div style={{ background: 'var(--astrovox-surface)', border: '1px solid var(--astrovox-border)', borderRadius: 'var(--astrovox-radius)', padding: '8px' }}>
            <h3 style={{ margin: '0 0 8px', fontSize: '11px', color: 'var(--astrovox-text-muted)', textTransform: 'uppercase', letterSpacing: '1px' }}>Analysis</h3>
            {analysis ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>Root Causes: {analysis.root_causes.length}</span>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>Leaves: {analysis.leaves.length}</span>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>Selected Upstream: {analysis.upstream.length}</span>
                <span style={{ fontSize: '10px', fontFamily: 'monospace', color: 'var(--astrovox-text)' }}>Selected Downstream: {analysis.downstream.length}</span>
              </div>
            ) : (
              <span style={{ fontSize: '10px', color: 'var(--astrovox-text-muted)' }}>Click Analyze to compute chain analysis</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
