import { useState, useCallback, useEffect } from 'react'
import { CRDTProvider, useCRDT } from './CRDTProvider'

const PRESENCE_COLORS = [
  '#06b6d4', '#f472b6', '#34d399', '#fbbf24', '#ef4444',
  '#8b5cf6', '#3b82f6', '#10b981', '#f97316', '#6366f1'
]

export function CollaborationProvider({ children, documentId, currentUser }) {
  const userId = currentUser?.id || 'anonymous'
  const userColor = PRESENCE_COLORS[Math.abs(hashCode(userId)) % PRESENCE_COLORS.length]

  return (
    <CRDTProvider documentId={documentId} userId={userId}>
      <PresenceSync userId={userId} userName={currentUser?.name || 'Anonymous'} userColor={userColor} />
      {children}
    </CRDTProvider>
  )
}

function hashCode(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return hash
}

function PresenceSync({ userId, userName, userColor }) {
  const { addPeer, removePeer, isConnected } = useCRDT()

  useEffect(() => {
    if (!isConnected) return
    addPeer(userId, { name: userName, color: userColor })

    const broadcast = () => {
      if (navigator.onLine) {
        localStorage.setItem('astrovox-presence', JSON.stringify({
          userId,
          name: userName,
          color: userColor,
          lastSeen: Date.now()
        }))
      }
    }

    broadcast()
    const interval = setInterval(broadcast, 5000)
    return () => {
      removePeer(userId)
      clearInterval(interval)
    }
  }, [userId, userName, userColor, isConnected, addPeer, removePeer])

  return null
}

export function useCollaboration() {
  const crdt = useCRDT()
  const [cursorPosition, setCursorPosition] = useState(null)
  const [selectionRange, setSelectionRange] = useState(null)

  const broadcastCursor = useCallback((position) => {
    setCursorPosition(position)
  }, [])

  const broadcastSelection = useCallback((range) => {
    setSelectionRange(range)
  }, [])

  return {
    ...crdt,
    cursorPosition,
    selectionRange,
    broadcastCursor,
    broadcastSelection
  }
}
