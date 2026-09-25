import { useState, useEffect, useCallback } from 'react'
import { createStorage } from '../utils/storage'
import { isOnline } from '../utils/platform'
import { SyncStatus, SyncQueueItem } from '../types'

const SYNC_STORAGE = createStorage('sync')
const SYNC_QUEUE_KEY = 'astrovox-sync-queue'

export function useOfflineSyncQueue(syncFn) {
  const [queue, setQueue] = useState([])
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState(null)
  const [stats, setStats] = useState({ synced: 0, failed: 0, pending: 0 })

  useEffect(() => {
    loadQueue()
  }, [])

  const loadQueue = useCallback(() => {
    try {
      const saved = SYNC_STORAGE.get(SYNC_QUEUE_KEY)
      if (Array.isArray(saved)) {
        setQueue(saved)
        setStats({
          synced: saved.filter(i => i.status === SyncStatus.SYNCED).length,
          failed: saved.filter(i => i.status === SyncStatus.FAILED).length,
          pending: saved.filter(i => i.status === SyncStatus.PENDING || i.status === SyncStatus.SYNCING).length
        })
      }
    } catch (e) {
      console.error('Failed to load sync queue:', e)
    }
  }, [])

  const persistQueue = useCallback((newQueue) => {
    try {
      SYNC_STORAGE.set(SYNC_QUEUE_KEY, newQueue)
    } catch {
      console.warn('Sync queue persistence failed')
    }
  }, [])

  const enqueue = useCallback((action, data) => {
    const item = new SyncQueueItem(action, data)
    const newQueue = [...queue, item]
    setQueue(newQueue)
    persistQueue(newQueue)
    setStats(prev => ({ ...prev, pending: prev.pending + 1 }))
    return item
  }, [queue, persistQueue])

  const enqueueMessage = useCallback((message) => {
    return enqueue('send_message', message)
  }, [enqueue])

  const enqueueAction = useCallback((action, payload) => {
    return enqueue(action, payload)
  }, [enqueue])

  const syncOne = useCallback(async (item) => {
    if (!isOnline() || !syncFn) return item

    try {
      setQueue(prev => prev.map(i => i.id === item.id ? { ...i, status: SyncStatus.SYNCING } : i))
      await syncFn(item.action, item.data)
      const updated = { ...item, status: SyncStatus.SYNCED, syncedAt: new Date().toISOString() }
      setQueue(prev => prev.map(i => i.id === item.id ? updated : i))
      setStats(prev => ({
        synced: prev.synced + 1,
        failed: prev.failed,
        pending: prev.pending - 1
      }))
      return updated
    } catch (e) {
      const failed = { ...item, status: SyncStatus.FAILED, error: e.message, retries: item.retries + 1 }
      setQueue(prev => prev.map(i => i.id === item.id ? failed : i))
      setStats(prev => ({
        synced: prev.synced,
        failed: prev.failed + 1,
        pending: prev.pending - 1
      }))
      return failed
    }
  }, [syncFn])

  const syncAll = useCallback(async () => {
    if (!isOnline() || syncing) return { synced: 0, failed: 0 }

    const pending = queue.filter(i => i.status === SyncStatus.PENDING || i.status === SyncStatus.FAILED)
    if (pending.length === 0) return { synced: 0, failed: 0 }

    setSyncing(true)
    const results = { synced: 0, failed: 0 }

    for (const item of pending) {
      if (item.retries >= 3) {
        setQueue(prev => prev.filter(i => i.id !== item.id))
        continue
      }
      const result = await syncOne(item)
      if (result.status === SyncStatus.SYNCED) {
        results.synced++
      } else {
        results.failed++
      }
    }

    const remaining = queue.filter(i => i.status !== SyncStatus.SYNCED)
    setQueue(remaining)
    persistQueue(remaining)
    setLastSync(new Date().toISOString())
    setSyncing(false)
    setStats(prev => ({
      synced: prev.synced + results.synced,
      failed: prev.failed,
      pending: remaining.filter(i => i.status === SyncStatus.PENDING || i.status === SyncStatus.SYNCING).length
    }))

    return results
  }, [queue, syncing, syncOne, persistQueue])

  const clearSynced = useCallback(() => {
    const remaining = queue.filter(i => i.status !== SyncStatus.SYNCED)
    setQueue(remaining)
    persistQueue(remaining)
    setStats(prev => ({
      synced: prev.synced,
      failed: prev.failed,
      pending: remaining.filter(i => i.status === SyncStatus.PENDING || i.status === SyncStatus.SYNCING).length
    }))
  }, [queue, persistQueue])

  const clearAll = useCallback(() => {
    setQueue([])
    persistQueue([])
    setStats({ synced: 0, failed: 0, pending: 0 })
    setLastSync(null)
  }, [persistQueue])

  const retryFailed = useCallback(async () => {
    setQueue(prev => prev.map(i => i.status === SyncStatus.FAILED ? { ...i, status: SyncStatus.PENDING } : i))
    await syncAll()
  }, [syncAll])

  useEffect(() => {
    if (!isOnline()) return
    const timer = setTimeout(() => {
      if (queue.some(i => i.status === SyncStatus.PENDING)) {
        syncAll()
      }
    }, 2000)
    return () => clearTimeout(timer)
  }, [isOnline, queue, syncAll])

  return {
    queue,
    syncing,
    lastSync,
    stats,
    enqueue,
    enqueueMessage,
    enqueueAction,
    syncOne,
    syncAll,
    clearSynced,
    clearAll,
    retryFailed,
    refresh: loadQueue
  }
}
