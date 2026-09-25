import { useState, useEffect, useRef, useCallback } from 'react'
import { HOLOGRAPHIC_CONFIG, HOLOGRAPHIC_COLORS } from '../../utils/holographic/HolographicConfig'

export function useKnowledgeGraph3D() {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [isExplorerActive, setIsExplorerActive] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)
  const [hoveredNode, setHoveredNode] = useState(null)
  const [layout, setLayout] = useState('force_directed')
  const [cameraPosition, setCameraPosition] = useState({ x: 0, y: 0, z: 5 })
  const [cameraRotation, setCameraRotation] = useState({ x: 0, y: 0 })
  const animationRef = useRef(null)

  const layoutAlgorithms = {
    force_directed: forceDirectedLayout,
    hierarchical: hierarchicalLayout,
    circular: circularLayout,
    spherical: sphericalLayout
  }

  const createNode = useCallback((id, label, type = 'concept', options = {}) => ({
    id,
    label,
    type,
    x: options.x || (Math.random() - 0.5) * 4,
    y: options.y || (Math.random() - 0.5) * 4,
    z: options.z || (Math.random() - 0.5) * 4,
    velocity: { x: 0, y: 0, z: 0 },
    size: options.size || 0.2,
    color: getNodeColor(type),
    connections: 0,
    weight: options.weight || 1,
    metadata: options.metadata || {},
    ...options
  }), [])

  const createEdge = useCallback((source, target, type = 'related', options = {}) => ({
    id: `${source}-${target}-${type}`,
    source,
    target,
    type,
    weight: options.weight || 1,
    color: getEdgeColor(type),
    metadata: options.metadata || {},
    ...options
  }), [])

  const getNodeColor = useCallback((type) => {
    const colors = {
      concept: HOLOGRAPHIC_COLORS.primary,
      entity: HOLOGRAPHIC_COLORS.secondary,
      event: HOLOGRAPHIC_COLORS.accent,
      attribute: HOLOGRAPHIC_COLORS.tertiary,
      relationship: HOLOGRAPHIC_COLORS.consciousness,
      memory: HOLOGRAPHIC_COLORS.dream,
      skill: HOLOGRAPHIC_COLORS.quantum,
      goal: HOLOGRAPHIC_COLORS.success,
      question: HOLOGRAPHIC_COLORS.warning
    }
    return colors[type] || HOLOGRAPHIC_COLORS.primary
  }, [])

  const getEdgeColor = useCallback((type) => {
    const colors = {
      related: 'rgba(6, 182, 212, 0.4)',
      part_of: 'rgba(244, 114, 182, 0.4)',
      causes: 'rgba(239, 68, 68, 0.4)',
      enables: 'rgba(52, 211, 153, 0.4)',
      contradicts: 'rgba(251, 191, 36, 0.4)',
      similar: 'rgba(167, 139, 250, 0.4)',
      contains: 'rgba(103, 232, 249, 0.4)'
    }
    return colors[type] || colors.related
  }, [])

  const addNode = useCallback((node) => {
    setNodes(prev => [...prev, node])
    return node
  }, [])

  const addEdge = useCallback((edge) => {
    setEdges(prev => [...prev, edge])
    setNodes(prev => prev.map(node => {
      if (node.id === edge.source || node.id === edge.target) {
        return { ...node, connections: node.connections + 1 }
      }
      return node
    }))
    return edge
  }, [])

  const removeNode = useCallback((nodeId) => {
    setNodes(prev => prev.filter(n => n.id !== nodeId))
    setEdges(prev => prev.filter(e => e.source !== nodeId && e.target !== nodeId))
  }, [])

  const removeEdge = useCallback((edgeId) => {
    setEdges(prev => prev.filter(e => e.id !== edgeId))
  }, [])

  const forceDirectedLayout = useCallback((nodesArr, edgesArr, iterations = 100) => {
    const layoutNodes = nodesArr.map(n => ({ ...n, velocity: { x: 0, y: 0, z: 0 } }))
    const k = 0.5

    for (let iter = 0; iter < iterations; iter++) {
      layoutNodes.forEach(node => {
        layoutNodes.forEach(other => {
          if (node.id === other.id) return

          const dx = node.x - other.x
          const dy = node.y - other.y
          const dz = node.z - other.z
          const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1

          const force = k * k / distance
          node.velocity.x += (dx / distance) * force * 0.1
          node.velocity.y += (dy / distance) * force * 0.1
          node.velocity.z += (dz / distance) * force * 0.1
        })
      })

      edgesArr.forEach(edge => {
        const source = layoutNodes.find(n => n.id === edge.source)
        const target = layoutNodes.find(n => n.id === edge.target)
        if (!source || !target) return

        const dx = target.x - source.x
        const dy = target.y - source.y
        const dz = target.z - source.z
        const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1

        const force = (distance - k) * 0.1
        source.velocity.x += (dx / distance) * force
        source.velocity.y += (dy / distance) * force
        source.velocity.z += (dz / distance) * force
        target.velocity.x -= (dx / distance) * force
        target.velocity.y -= (dy / distance) * force
        target.velocity.z -= (dz / distance) * force
      })

      layoutNodes.forEach(node => {
        node.velocity.x *= 0.9
        node.velocity.y *= 0.9
        node.velocity.z *= 0.9
        node.x += node.velocity.x * 0.1
        node.y += node.velocity.y * 0.1
        node.z += node.velocity.z * 0.1
      })
    }

    return layoutNodes
  }, [])

  const hierarchicalLayout = useCallback((nodesArr, edgesArr) => {
    const levels = {}
    const visited = new Set()

    const assignLevel = (nodeId, level) => {
      if (visited.has(nodeId)) return
      visited.add(nodeId)

      levels[nodeId] = level
      const outgoingEdges = edgesArr.filter(e => e.source === nodeId)

      outgoingEdges.forEach(edge => {
        assignLevel(edge.target, level + 1)
      })
    }

    const roots = nodesArr.filter(node => !edgesArr.some(e => e.target === node.id))
    roots.forEach(root => assignLevel(root.id, 0))

    nodesArr.forEach(node => {
      if (!visited.has(node.id)) {
        assignLevel(node.id, 0)
      }
    })

    const maxLevel = Math.max(...Object.values(levels), 0)
    const nodesAtLevel = {}

    nodesArr.forEach(node => {
      const level = levels[node.id] || 0
      if (!nodesAtLevel[level]) nodesAtLevel[level] = []
      nodesAtLevel[level].push(node)
    })

    return nodesArr.map(node => {
      const level = levels[node.id] || 0
      const nodesInLevel = nodesAtLevel[level] || [node]
      const indexInLevel = nodesInLevel.indexOf(node)
      const angle = (indexInLevel / nodesInLevel.length) * Math.PI * 2
      const radius = 1 + level * 0.5

      return {
        ...node,
        x: Math.cos(angle) * radius,
        y: level * 0.5,
        z: Math.sin(angle) * radius
      }
    })
  }, [])

  const circularLayout = useCallback((nodesArr) => {
    const radius = 2
    const angleStep = (Math.PI * 2) / nodesArr.length

    return nodesArr.map((node, index) => ({
      ...node,
      x: Math.cos(angleStep * index) * radius,
      y: 0,
      z: Math.sin(angleStep * index) * radius
    }))
  }, [])

  const sphericalLayout = useCallback((nodesArr) => {
    const radius = 2
    const phi = Math.PI * (3 - Math.sqrt(5))

    return nodesArr.map((node, index) => {
      const y = 1 - (index / (nodesArr.length - 1)) * 2
      const radiusAtY = Math.sqrt(1 - y * y)
      const theta = phi * index

      return {
        ...node,
        x: Math.cos(theta) * radiusAtY * radius,
        y: y * radius,
        z: Math.sin(theta) * radiusAtY * radius
      }
    })
  }, [])

  const applyLayout = useCallback((algorithm) => {
    const layoutFn = layoutAlgorithms[algorithm] || forceDirectedLayout
    const layoutNodes = layoutFn(nodes, edges)
    setNodes(layoutNodes)
    setLayout(algorithm)
  }, [nodes, edges, layoutAlgorithms, forceDirectedLayout])

  const startExplorer = useCallback(() => {
    setIsExplorerActive(true)
    animateExplorer()
  }, [])

  const stopExplorer = useCallback(() => {
    setIsExplorerActive(false)
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
  }, [])

  const animateExplorer = useCallback(() => {
    if (!isExplorerActive) return

    const time = Date.now() * 0.001

    setNodes(prev => prev.map(node => {
      const hoverBoost = hoveredNode?.id === node.id ? 1.2 : 1
      const pulse = Math.sin(time * 2 + node.x) * 0.02
      return {
        ...node,
        size: (node.size || 0.2) * hoverBoost + pulse
      }
    }))

    animationRef.current = requestAnimationFrame(animateExplorer)
  }, [isExplorerActive, hoveredNode])

  const exploreFromNode = useCallback((nodeId) => {
    setSelectedNode(nodeId)
  }, [])

  const zoomToNode = useCallback((nodeId) => {
    const node = nodes.find(n => n.id === nodeId)
    if (node) {
      setCameraPosition({
        x: node.x,
        y: node.y,
        z: node.z + 3
      })
    }
  }, [nodes])

  const exportGraph = useCallback(() => {
    return {
      nodes,
      edges,
      layout,
      camera: { position: cameraPosition, rotation: cameraRotation },
      exportedAt: Date.now()
    }
  }, [nodes, edges, layout, cameraPosition, cameraRotation])

  const importGraph = useCallback((graphData) => {
    if (graphData.nodes) setNodes(graphData.nodes)
    if (graphData.edges) setEdges(graphData.edges)
    if (graphData.layout) setLayout(graphData.layout)
    if (graphData.camera) {
      setCameraPosition(graphData.camera.position)
      setCameraRotation(graphData.camera.rotation)
    }
  }, [])

  useEffect(() => {
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [])

  return {
    nodes,
    edges,
    isExplorerActive,
    selectedNode,
    hoveredNode,
    layout,
    cameraPosition,
    cameraRotation,
    createNode,
    createEdge,
    addNode,
    addEdge,
    removeNode,
    removeEdge,
    applyLayout,
    startExplorer,
    stopExplorer,
    exploreFromNode,
    zoomToNode,
    setSelectedNode,
    setHoveredNode,
    exportGraph,
    importGraph,
    layoutAlgorithms
  }
}
