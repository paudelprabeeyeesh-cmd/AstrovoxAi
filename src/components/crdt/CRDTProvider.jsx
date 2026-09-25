import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'

const CRDTContext = createContext(null)

export function CRDTProvider({ children, documentId, userId }) {
  const [peers, setPeers] = useState(new Map())
  const [localState, setLocalState] = useState({})
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef(null)
  const clockRef = useRef(0)
  const pendingOpsRef = useRef([])

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/crdt/${documentId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      ws.send(JSON.stringify({ type: 'join', userId, documentId }))
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        handleRemoteOperation(message)
      } catch (e) {
        console.error('Failed to parse CRDT message:', e)
      }
    }

    ws.onclose = () => {
      setIsConnected(false)
      setTimeout(() => {
        if (documentId) connect()
      }, 3000)
    }

    ws.onerror = (err) => {
      console.error('CRDT WebSocket error:', err)
    }

    return () => {
      ws.close()
    }
  }, [documentId, userId])

  const connect = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState === WebSocket.OPEN) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/crdt/${documentId}`
    wsRef.current = new WebSocket(wsUrl)
  }, [documentId])

  const generateOperationId = useCallback(() => {
    return `${userId}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
  }, [userId])

  const handleRemoteOperation = useCallback((op) => {
    if (op.userId === userId) return
    setLocalState(prev => applyOperation(prev, op))
  }, [userId])

  const applyOperation = (state, op) => {
    switch (op.type) {
      case 'insert':
        return {
          ...state,
          [op.path]: {
            ...state[op.path],
            value: op.value,
            clock: Math.max(state[op.path]?.clock || 0, op.clock),
            author: op.userId
          }
        }
      case 'delete': {
        const next = { ...state }
        delete next[op.path]
        return next
      }
      case 'update':
        return {
          ...state,
          [op.path]: {
            ...state[op.path],
            ...op.changes,
            clock: Math.max(state[op.path]?.clock || 0, op.clock)
          }
        }
      default:
        return state
    }
  }

  const sendOperation = useCallback((type, payload) => {
    const op = {
      id: generateOperationId(),
      type,
      ...payload,
      clock: ++clockRef.current,
      userId,
      timestamp: Date.now()
    }
    pendingOpsRef.current.push(op)
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(op))
    }
    setLocalState(prev => applyOperation(prev, op))
    return op
  }, [userId, generateOperationId])

  const insert = useCallback((path, value) => {
    return sendOperation('insert', { path, value })
  }, [sendOperation])

  const remove = useCallback((path) => {
    return sendOperation('delete', { path })
  }, [sendOperation])

  const update = useCallback((path, changes) => {
    return sendOperation('update', { path, changes })
  }, [sendOperation])

  const addPeer = useCallback((peerId, metadata) => {
    setPeers(prev => new Map(prev).set(peerId, { ...metadata, joinedAt: Date.now() }))
  }, [])

  const removePeer = useCallback((peerId) => {
    setPeers(prev => {
      const next = new Map(prev)
      next.delete(peerId)
      return next
    })
  }, [])

  const value = {
    documentId,
    userId,
    isConnected,
    peers: Array.from(peers.values()),
    localState,
    insert,
    remove,
    update,
    addPeer,
    removePeer,
    connect
  }

  return <CRDTContext.Provider value={value}>{children}</CRDTContext.Provider>
}

export function useCRDT() {
  const context = useContext(CRDTContext)
  if (!context) throw new Error('useCRDT must be used within CRDTProvider')
  return context
}
