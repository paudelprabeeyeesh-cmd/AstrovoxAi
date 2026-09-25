import { useState, useEffect, useCallback } from 'react'

const SYNC_KEYS = {
  queue: 'astrovox-sync-queue',
  lastSync: 'astrovox-last-sync',
  conflicts: 'astrovox-sync-conflicts'
}

export function useBackgroundSync() {
  const [syncStatus, setSyncStatus] = useState('idle')
  const [lastSyncTime, setLastSyncTime] = useState(null)
  const [syncErrors, setSyncErrors] = useState([])

  useEffect(() => {
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      navigator.serviceWorker.ready.then(registration => {
        return registration.sync.register('astrovox-sync')
      }).catch(err => {
        console.error('Background sync registration failed:', err)
      })
    }

    const saved = localStorage.getItem(SYNC_KEYS.lastSync)
    if (saved) {
      setLastSyncTime(new Date(saved))
    }
  }, [])

  const addToSyncQueue = useCallback((item) => {
    const queue = JSON.parse(localStorage.getItem(SYNC_KEYS.queue) || '[]')
    queue.push({
      ...item,
      id: crypto.randomUUID(),
      queuedAt: new Date().toISOString(),
      attempts: 0
    })
    localStorage.setItem(SYNC_KEYS.queue, JSON.stringify(queue))

    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      navigator.serviceWorker.ready.then(registration => {
        return registration.sync.register('astrovox-sync')
      }).catch(() => {
        processSyncQueue()
      })
    } else {
      processSyncQueue()
    }
  }, [])

  const processSyncQueue = useCallback(async () => {
    setSyncStatus('syncing')
    const queue = JSON.parse(localStorage.getItem(SYNC_KEYS.queue) || '[]')

    const results = []
    for (const item of queue) {
      try {
        const response = await fetch('/api/sync/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item)
        })
        if (response.ok) {
          results.push({ ...item, synced: true })
        } else {
          results.push({ ...item, synced: false, error: `HTTP ${response.status}` })
        }
      } catch (error) {
        results.push({ ...item, synced: false, error: error.message })
      }
    }

    const failed = results.filter(r => !r.synced)
    localStorage.setItem(SYNC_KEYS.queue, JSON.stringify(failed))
    localStorage.setItem(SYNC_KEYS.lastSync, new Date().toISOString())
    setLastSyncTime(new Date())
    setSyncStatus(failed.length === 0 ? 'complete' : 'partial')
    setSyncErrors(failed.map(f => f.error))

    return { synced: results.filter(r => r.synced).length, failed: failed.length }
  }, [])

  const resolveConflict = useCallback((conflictId, resolution) => {
    const conflicts = JSON.parse(localStorage.getItem(SYNC_KEYS.conflicts) || '[]')
    const index = conflicts.findIndex(c => c.id === conflictId)
    if (index !== -1) {
      conflicts[index] = { ...conflicts[index], resolution, resolvedAt: new Date().toISOString() }
      localStorage.setItem(SYNC_KEYS.conflicts, JSON.stringify(conflicts))
    }
  }, [])

  const retryFailed = useCallback(async () => {
    setSyncStatus('syncing')
    const queue = JSON.parse(localStorage.getItem(SYNC_KEYS.queue) || '[]')
    const retryable = queue.filter(item => item.attempts < 3)

    for (const item of retryable) {
      item.attempts += 1
      try {
        const response = await fetch('/api/sync/process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item)
        })
        if (response.ok) {
          const newQueue = queue.filter(i => i.id !== item.id)
          localStorage.setItem(SYNC_KEYS.queue, JSON.stringify(newQueue))
        }
      } catch (error) {
        console.error('Retry failed:', error)
      }
    }

    setSyncStatus('idle')
  }, [])

  return {
    syncStatus,
    lastSyncTime,
    syncErrors,
    addToSyncQueue,
    processSyncQueue,
    resolveConflict,
    retryFailed
  }
}
