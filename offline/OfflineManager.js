import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEYS = {
  messages: 'astrovox-offline-messages',
  pending: 'astrovox-pending-sync',
  settings: 'astrovox-offline-settings'
}

export function useOfflineMode() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [pendingSync, setPendingSync] = useState([])
  const [queueSize, setQueueSize] = useState(0)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    const saved = localStorage.getItem(STORAGE_KEYS.pending)
    if (saved) {
      try {
        setPendingSync(JSON.parse(saved))
        setQueueSize(JSON.parse(saved).length)
      } catch (e) {
        console.error('Failed to load pending sync:', e)
      }
    }

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const saveMessageOffline = useCallback((message) => {
    const saved = localStorage.getItem(STORAGE_KEYS.messages) || '[]'
    const messages = JSON.parse(saved)
    messages.push({ ...message, offline: true, savedAt: new Date().toISOString() })
    localStorage.setItem(STORAGE_KEYS.messages, JSON.stringify(messages))

    const pending = JSON.parse(localStorage.getItem(STORAGE_KEYS.pending) || '[]')
    pending.push(message)
    localStorage.setItem(STORAGE_KEYS.pending, JSON.stringify(pending))
    setQueueSize(pending.length)
  }, [])

  const syncPendingMessages = useCallback(async (syncFn) => {
    const pending = JSON.parse(localStorage.getItem(STORAGE_KEYS.pending) || '[]')
    if (pending.length === 0) return

    const results = []
    for (const message of pending) {
      try {
        await syncFn(message)
        results.push({ ...message, synced: true })
      } catch (error) {
        results.push({ ...message, synced: false, error: error.message })
      }
    }

    const failed = results.filter(r => !r.synced)
    localStorage.setItem(STORAGE_KEYS.pending, JSON.stringify(failed))
    setQueueSize(failed.length)
    setPendingSync(failed)

    return { synced: results.filter(r => r.synced).length, failed: failed.length }
  }, [])

  const clearOfflineData = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.messages)
    localStorage.removeItem(STORAGE_KEYS.pending)
    setQueueSize(0)
    setPendingSync([])
  }, [])

  return {
    isOnline,
    pendingSync,
    queueSize,
    saveMessageOffline,
    syncPendingMessages,
    clearOfflineData
  }
}
