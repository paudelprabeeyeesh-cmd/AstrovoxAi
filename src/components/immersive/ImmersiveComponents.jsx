import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'
import { useKnowledgeGraph3D } from '../../hooks/holographic/useKnowledgeGraph3D'
import { useQuantumState } from '../../hooks/holographic/useQuantumState'
import { useNeuralInterface } from '../../hooks/holographic/useNeuralInterface'
import { useDreamState } from '../../hooks/holographic/useDreamState'

export function KnowledgeGraphExplorer({ className = '', style = {} }) {
  const canvasRef = useRef(null)
  const {
    nodes,
    edges,
    selectedNode,
    hoveredNode,
    layout,
    addNode,
    addEdge,
    exploreFromNode,
    zoomToNode,
    setSelectedNode,
    setHoveredNode,
    startExplorer,
    stopExplorer,
    isExplorerActive,
    applyLayout,
    layoutAlgorithms
  } = useKnowledgeGraph3D()

  const [viewMode, setViewMode] = useState('3d')
  const [filters, setFilters] = useState({ types: [], minWeight: 0 })

  useEffect(() => {
    startExplorer()
    return () => stopExplorer()
  }, [startExplorer, stopExplorer])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const { width, height } = canvas

    const animate = () => {
      ctx.clearRect(0, 0, width, height)

      const camera = {
        x: width / 2,
        y: height / 2,
        zoom: 1
      }

      const project3D = (node) => {
        const scale = 200 / (node.z + 5)
        return {
          x: node.x * scale + camera.x,
          y: node.y * scale + camera.y,
          scale
        }
      }

      edges.forEach(edge => {
        const source = nodes.find(n => n.id === edge.source)
        const target = nodes.find(n => n.id === edge.target)
        if (!source || !target) return

        const projSource = project3D(source)
        const projTarget = project3D(target)

        ctx.beginPath()
        ctx.moveTo(projSource.x, projSource.y)
        ctx.lineTo(projTarget.x, projTarget.y)
        ctx.strokeStyle = edge.color
        ctx.lineWidth = (edge.weight || 1) * 0.5
        ctx.stroke()
      })

      nodes.forEach(node => {
        const proj = project3D(node)
        const isSelected = selectedNode === node.id
        const isHovered = hoveredNode === node.id
        const radius = (node.size || 0.2) * proj.scale * 20

        ctx.beginPath()
        ctx.arc(proj.x, proj.y, radius, 0, Math.PI * 2)
        ctx.fillStyle = node.color
        ctx.globalAlpha = isSelected ? 1 : isHovered ? 0.8 : 0.6
        ctx.fill()
        ctx.globalAlpha = 1

        if (isSelected || isHovered) {
          ctx.beginPath()
          ctx.arc(proj.x, proj.y, radius + 5, 0, Math.PI * 2)
          ctx.strokeStyle = HOLOGRAPHIC_COLORS.accent
          ctx.lineWidth = 2
          ctx.stroke()
        }

        ctx.fillStyle = 'var(--astrovox-text)'
        ctx.font = '10px Inter'
        ctx.textAlign = 'center'
        ctx.fillText(node.label, proj.x, proj.y + radius + 15)
      })

      requestAnimationFrame(animate)
    }

    animate()
  }, [nodes, edges, selectedNode, hoveredNode])

  const handleCanvasClick = useCallback((e) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const clickedNode = nodes.find(node => {
      const scale = 200 / (node.z + 5)
      const projX = node.x * scale + canvas.width / 2
      const projY = node.y * scale + canvas.height / 2
      const radius = (node.size || 0.2) * scale * 20
      const distance = Math.sqrt((x - projX) ** 2 + (y - projY) ** 2)
      return distance < radius
    })

    if (clickedNode) {
      setSelectedNode(clickedNode.id)
      zoomToNode(clickedNode.id)
    } else {
      setSelectedNode(null)
    }
  }, [nodes, setSelectedNode, zoomToNode])

  const handleCanvasHover = useCallback((e) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const hovered = nodes.find(node => {
      const scale = 200 / (node.z + 5)
      const projX = node.x * scale + canvas.width / 2
      const projY = node.y * scale + canvas.height / 2
      const radius = (node.size || 0.2) * scale * 20
      const distance = Math.sqrt((x - projX) ** 2 + (y - projY) ** 2)
      return distance < radius
    })

    setHoveredNode(hovered?.id || null)
  }, [nodes, setHoveredNode])

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.floatingPanel,
        ...style
      }}
    >
      <div style={{
        padding: '16px',
        borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3 style={{ margin: 0, color: HOLOGRAPHIC_COLORS.accent, fontSize: '16px' }}>
          Knowledge Graph
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={layout}
            onChange={(e) => applyLayout(e.target.value)}
            style={{
              ...HOLOGRAPHIC_LAYOUTS.hologramInput,
              padding: '6px 12px',
              fontSize: '12px'
            }}
          >
            {Object.keys(layoutAlgorithms).map(algo => (
              <option key={algo} value={algo}>
                {algo.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        onMouseMove={handleCanvasHover}
        style={{
          width: '100%',
          height: '400px',
          cursor: 'pointer'
        }}
      />
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '11px',
          color: 'var(--astrovox-text-muted)'
      }}>
        <span>{nodes.length} nodes</span>
        <span>{edges.length} connections</span>
      </div>
    </div>
  )
}

export function QuantumStateVisualization({ className = '', style = {} }) {
  const {
    qubits,
    isSimulating,
    coherence,
    entanglement,
    measurements,
    startSimulation,
    stopSimulation,
    reset,
    applyGate,
    measure,
    measureAll
  } = useQuantumState()

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        ...style
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, color: HOLOGRAPHIC_COLORS.accent, fontSize: '16px' }}>
          Quantum State
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={isSimulating ? stopSimulation : startSimulation} style={{
            ...HOLOGRAPHIC_LAYOUTS.hologramButton,
            padding: '6px 12px',
            fontSize: '12px',
            cursor: 'pointer'
          }}>
            {isSimulating ? 'Stop' : 'Simulate'}
          </button>
          <button onClick={reset} style={{
            ...HOLOGRAPHIC_LAYOUTS.hologramButton,
            padding: '6px 12px',
            fontSize: '12px',
            cursor: 'pointer'
          }}>
            Reset
          </button>
        </div>
      </div>
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '12px' }}>Coherence</span>
          <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
            {(coherence * 100).toFixed(1)}%
          </span>
        </div>
        <div style={{
          height: '8px',
          background: 'rgba(167, 139, 250, 0.1)',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          <div style={{
            width: `${coherence * 100}%`,
            height: '100%',
            background: HOLOGRAPHIC_COLORS.quantum,
            borderRadius: '4px',
            transition: 'width 0.3s ease'
          }} />
        </div>
      </div>
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '12px',
        justifyContent: 'center'
      }}>
        {qubits.map((qubit, index) => (
          <div
            key={index}
            style={{
              width: '60px',
              height: '60px',
              borderRadius: '50%',
              border: `2px solid ${HOLOGRAPHIC_COLORS.quantum}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: `rgba(167, 139, 250, ${qubit.amplitude * 0.2})`,
              position: 'relative'
            }}
          >
            <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '18px', fontWeight: 'bold' }}>
              {qubit.measured ? qubit.value : 'ψ'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export function DreamStateInterface({ className = '', style = {} }) {
  const {
    isDreaming,
    dreamPhase,
    dreamClarity,
    lucidityLevel,
    dreamScenes,
    dreamNarrative,
    isLucidAssistantActive,
    enterDreamState,
    exitDreamState,
    activateLucidAssistant,
    stabilizeLucidity,
    performRealityCheck,
    navigateMemoryPalace
  } = useDreamState()

  const dreamPhases = ['drowsy', 'light_sleep', 'rem', 'deep_sleep', 'lucid']

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.floatingPanel,
        ...style
      }}
    >
      <div style={{
        padding: '16px',
        borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <h3 style={{ margin: 0, color: HOLOGRAPHIC_COLORS.accent, fontSize: '16px' }}>
          Dream State Interface
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          {!isDreaming ? (
            <select
              onChange={(e) => enterDreamState(e.target.value)}
              style={{
                ...HOLOGRAPHIC_LAYOUTS.hologramInput,
                padding: '6px 12px',
                fontSize: '12px'
              }}
            >
              <option value="">Enter dream phase...</option>
              {dreamPhases.map(phase => (
                <option key={phase} value={phase}>
                  {phase.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>
          ) : (
            <button onClick={exitDreamState} style={{
              ...HOLOGRAPHIC_LAYOUTS.hologramButton,
              padding: '6px 12px',
              fontSize: '12px',
              cursor: 'pointer'
            }}>
              Wake Up
            </button>
          )}
        </div>
      </div>
      {isDreaming && (
        <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '12px' }}>Dream Clarity</span>
              <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
                {(dreamClarity * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{
              height: '6px',
              background: 'rgba(167, 139, 250, 0.1)',
              borderRadius: '3px',
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${dreamClarity * 100}%`,
                height: '100%',
                background: HOLOGRAPHIC_COLORS.dream,
                borderRadius: '3px'
              }} />
            </div>
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ color: HOLOGRAPHIC_COLORS.accent, fontSize: '12px' }}>Lucidity</span>
              <span style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
                {(lucidityLevel * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{
              height: '6px',
              background: 'rgba(244, 114, 182, 0.1)',
              borderRadius: '3px',
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${lucidityLevel * 100}%`,
                height: '100%',
                background: HOLOGRAPHIC_COLORS.consciousness,
                borderRadius: '3px'
              }} />
            </div>
          </div>
          {dreamNarrative && (
            <div style={{
              padding: '12px',
              background: 'rgba(167, 139, 250, 0.1)',
              borderRadius: '8px',
              border: '1px solid rgba(167, 139, 250, 0.3)'
            }}>
              <p style={{ margin: 0, color: 'var(--astrovox-text)', fontSize: '13px', fontStyle: 'italic' }}>
                {dreamNarrative}
              </p>
            </div>
          )}
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={activateLucidAssistant} style={{
              ...HOLOGRAPHIC_LAYOUTS.hologramButton,
              padding: '8px 16px',
              fontSize: '12px',
              cursor: 'pointer'
            }}>
              Lucid Assistant
            </button>
            <button onClick={stabilizeLucidity} style={{
              ...HOLOGRAPHIC_LAYOUTS.hologramButton,
              padding: '8px 16px',
              fontSize: '12px',
              cursor: 'pointer'
            }}>
              Stabilize
            </button>
            <button onClick={performRealityCheck} style={{
              ...HOLOGRAPHIC_LAYOUTS.hologramButton,
              padding: '8px 16px',
              fontSize: '12px',
              cursor: 'pointer'
            }}>
              Reality Check
            </button>
          </div>
          {lucidityLevel > 0.5 && (
            <button onClick={() => navigateMemoryPalace('main_hall')} style={{
              ...HOLOGRAPHIC_LAYOUTS.hologramButton,
              padding: '8px 16px',
              fontSize: '12px',
              cursor: 'pointer'
            }}>
              Navigate Memory Palace
            </button>
          )}
        </div>
      )}
    </div>
  )
}
