export const PlatformType = {
  WEB: 'web',
  MOBILE: 'mobile',
  DESKTOP: 'desktop',
  EXTENSION: 'extension',
  EDITOR: 'editor'
}

export const StorageType = {
  LOCAL_STORAGE: 'localStorage',
  INDEXED_DB: 'indexedDB',
  SUPABASE: 'supabase',
  FILE_SYSTEM: 'fileSystem'
}

export const SyncStatus = {
  PENDING: 'pending',
  SYNCING: 'syncing',
  SYNCED: 'synced',
  FAILED: 'failed'
}

export class PlatformEvent {
  constructor(type, payload = {}) {
    this.type = type
    this.payload = payload
    this.timestamp = Date.now()
  }
}

export class SyncQueueItem {
  constructor(action, data) {
    this.id = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
    this.action = action
    this.data = data
    this.status = SyncStatus.PENDING
    this.createdAt = new Date().toISOString()
    this.retries = 0
  }
}
