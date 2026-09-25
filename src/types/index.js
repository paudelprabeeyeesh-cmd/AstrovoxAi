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

export const DeviceType = {
  WEB: 'web',
  MOBILE: 'mobile',
  DESKTOP: 'desktop',
  EXTENSION: 'extension',
  EDITOR: 'editor',
  WEARABLE: 'wearable',
  IOT: 'iot',
  VEHICLE: 'vehicle',
  HOME: 'home',
  WORK: 'work'
}

export const EnvironmentType = {
  HOME: 'home',
  WORK: 'work',
  PUBLIC: 'public',
  TRANSIT: 'transit',
  NATURE: 'nature',
  SOCIAL: 'social',
  QUIET: 'quiet',
  NOISY: 'noisy',
  PRIVATE: 'private',
  CROWDED: 'crowded'
}

export const PresenceMode = {
  AMBIENT: 'ambient',
  ACTIVE: 'active',
  PASSIVE: 'passive',
  COLLECTIVE: 'collective',
  TELEPATHIC: 'telepathic'
}

export const SocialPresenceStatus = {
  ALONE: 'alone',
  SMALL_GROUP: 'small_group',
  LARGE_GROUP: 'large_group',
  ONE_ON_ONE: 'one_on_one',
  PUBLIC: 'public',
  FOCUSED: 'focused'
}

export const HandoffStatus = {
  IDLE: 'idle',
  INITIATED: 'initiated',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
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
