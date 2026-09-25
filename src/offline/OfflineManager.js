import { useState, useEffect, useCallback, useRef } from 'react'

const STORAGE_KEYS = {
  messages: 'astrovox-offline-messages',
  pending: 'astrovox-pending-sync',
  settings: 'astrovox-offline-settings',
  cache: 'astrovox-cache-timestamp'
}

const SYNC_INTERVAL = 30000

export function useOfflineMode() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [pendingSync, setPendingSync] = useState([])
  const [queueSize, setQueueSize] = useState(0)
  const [lastSyncAt, setLastSyncAt] = useState(null)
  const syncIntervalRef = useRef(null)

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      triggerSync()
    }
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    const saved = localStorage.getItem(STORAGE_KEYS.pending)
    if (saved) {
      try {
        const pending = JSON.parse(saved)
        setPendingSync(pending)
        setQueueSize(pending.length)
      } catch (e) {
        console.error('Failed to load pending sync:', e)
      }
    }

    const savedTimestamp = localStorage.getItem(STORAGE_KEYS.cache)
    if (savedTimestamp) {
      setLastSyncAt(new Date(parseInt(savedTimestamp, 10)))
    }

    syncIntervalRef.current = setInterval(() => {
      if (navigator.onLine) {
        triggerSync()
      }
    }, SYNC_INTERVAL)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current)
      }
    }
  }, [])

  const triggerSync = useCallback(() => {
    const pending = JSON.parse(localStorage.getItem(STORAGE_KEYS.pending) || '[]')
    if (pending.length > 0) {
      setLastSyncAt(new Date())
      localStorage.setItem(STORAGE_KEYS.cache, Date.now().toString())
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
    if (pending.length === 0) return { synced: 0, failed: 0 }

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

    setLastSyncAt(new Date())
    localStorage.setItem(STORAGE_KEYS.cache, Date.now().toString())

    return { synced: results.filter(r => r.synced).length, failed: failed.length }
  }, [])

  const clearOfflineData = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.messages)
    localStorage.removeItem(STORAGE_KEYS.pending)
    localStorage.removeItem(STORAGE_KEYS.cache)
    setQueueSize(0)
    setPendingSync([])
    setLastSyncAt(null)
  }, [])

  const getCachedMessages = useCallback(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.messages)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  }, [])

  return {
    isOnline,
    pendingSync,
    queueSize,
    lastSyncAt,
    saveMessageOffline,
    syncPendingMessages,
    clearOfflineData,
    getCachedMessages
  }
}
