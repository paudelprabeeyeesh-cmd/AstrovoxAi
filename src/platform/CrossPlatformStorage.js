import { StorageAdapter, createStorage } from '../utils/storage'
import { PlatformType, StorageType } from '../types'

const MEMORY_STORE = new Map()
const INDEXED_DB_NAME = 'astrovox-store'
const INDEXED_DB_VERSION = 1

export class CrossPlatformStorage {
  constructor(options = {}) {
    this.namespace = options.namespace || 'astrovox'
    this.platform = options.platform || PlatformType.WEB
    this.adapters = new Map()
    this.primaryAdapter = null
    this.fallbackAdapter = null

    this.initAdapters(options)
  }

  initAdapters(options) {
    if (this.platform === PlatformType.WEB || this.platform === PlatformType.EXTENSION) {
      this.adapters.set(StorageType.LOCAL_STORAGE, new StorageAdapter(this.namespace))
      this.primaryAdapter = this.adapters.get(StorageType.LOCAL_STORAGE)
    }

    if (typeof indexedDB !== 'undefined') {
      this.adapters.set(StorageType.INDEXED_DB, new IndexedDBAdapter(this.namespace))
      if (!this.primaryAdapter) {
        this.primaryAdapter = this.adapters.get(StorageType.INDEXED_DB)
      }
      this.fallbackAdapter = this.adapters.get(StorageType.INDEXED_DB)
    }

    if (options.supabaseClient) {
      this.adapters.set(StorageType.SUPABASE, new SupabaseStorageAdapter(this.namespace, options.supabaseClient))
      if (!this.primaryAdapter) {
        this.primaryAdapter = this.adapters.get(StorageType.SUPABASE)
      }
    }

    if (this.platform === PlatformType.DESKTOP) {
      this.adapters.set(StorageType.FILE_SYSTEM, new FileSystemStorageAdapter(this.namespace))
      if (!this.primaryAdapter) {
        this.primaryAdapter = this.adapters.get(StorageType.FILE_SYSTEM)
      }
    }
  }

  get(key) {
    try {
      return this.primaryAdapter?.get(key) ?? this.fallbackAdapter?.get(key)
    } catch {
      return this.fallbackAdapter?.get(key) ?? null
    }
  }

  set(key, value) {
    const primaryOk = this.primaryAdapter?.set(key, value)
    if (primaryOk === false && this.fallbackAdapter) {
      return this.fallbackAdapter.set(key, value)
    }
    return primaryOk !== false
  }

  remove(key) {
    this.adapters.forEach(adapter => {
      try { adapter.remove(key) } catch {}
    })
  }

  clear() {
    this.adapters.forEach(adapter => {
      try { adapter.clear() } catch {}
    })
  }

  keys() {
    return this.primaryAdapter?.keys() || this.fallbackAdapter?.keys() || []
  }

  size() {
    return this.keys().length
  }

  has(key) {
    return this.keys().includes(key)
  }

  async getAsync(key) {
    if (this.fallbackAdapter?.getAsync) {
      return this.fallbackAdapter.getAsync(key)
    }
    return this.get(key)
  }

  async setAsync(key, value) {
    if (this.fallbackAdapter?.setAsync) {
      return this.fallbackAdapter.setAsync(key, value)
    }
    return this.set(key, value)
  }
}

class IndexedDBAdapter {
  constructor(namespace) {
    this.namespace = namespace
    this.db = null
  }

  async getDB() {
    if (this.db) return this.db
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(`${INDEXED_DB_NAME}-${this.namespace}`, INDEXED_DB_VERSION)
      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve(this.db)
      }
      request.onupgradeneeded = (event) => {
        const db = event.target.result
        if (!db.objectStoreNames.contains('kv')) {
          db.createObjectStore('kv', { keyPath: 'key' })
        }
      }
    })
  }

  async get(key) {
    try {
      const db = await this.getDB()
      return new Promise((resolve) => {
        const tx = db.transaction('kv', 'readonly')
        const store = tx.objectStore('kv')
        const req = store.get(key)
        req.onsuccess = () => resolve(req.result?.value ?? null)
        req.onerror = () => resolve(null)
      })
    } catch {
      return null
    }
  }

  async set(key, value) {
    try {
      const db = await this.getDB()
      return new Promise((resolve) => {
        const tx = db.transaction('kv', 'readwrite')
        const store = tx.objectStore('kv')
        const req = store.put({ key, value })
        req.onsuccess = () => resolve(true)
        req.onerror = () => resolve(false)
      })
    } catch {
      return false
    }
  }

  async remove(key) {
    try {
      const db = await this.getDB()
      return new Promise((resolve) => {
        const tx = db.transaction('kv', 'readwrite')
        const store = tx.objectStore('kv')
        const req = store.delete(key)
        req.onsuccess = () => resolve()
        req.onerror = () => resolve()
      })
    } catch {}
  }

  async clear() {
    try {
      const db = await this.getDB()
      return new Promise((resolve) => {
        const tx = db.transaction('kv', 'readwrite')
        const store = tx.objectStore('kv')
        const req = store.clear()
        req.onsuccess = () => resolve()
        req.onerror = () => resolve()
      })
    } catch {}
  }

  async keys() {
    try {
      const db = await this.getDB()
      return new Promise((resolve) => {
        const tx = db.transaction('kv', 'readonly')
        const store = tx.objectStore('kv')
        const req = store.getAllKeys()
        req.onsuccess = () => resolve(req.result || [])
        req.onerror = () => resolve([])
      })
    } catch {
      return []
    }
  }
}

class SupabaseStorageAdapter {
  constructor(namespace, client) {
    this.namespace = namespace
    this.client = client
  }

  async get(key) {
    try {
      const { data, error } = await this.client
        .from('app_storage')
        .select('value')
        .eq('namespace', this.namespace)
        .eq('key', key)
        .single()

      if (error) return null
      return data?.value ?? null
    } catch {
      return null
    }
  }

  async set(key, value) {
    try {
      const { error } = await this.client
        .from('app_storage')
        .upsert({ namespace: this.namespace, key, value, updated_at: new Date().toISOString() })

      return !error
    } catch {
      return false
    }
  }
}

class FileSystemStorageAdapter {
  constructor(namespace) {
    this.namespace = namespace
  }

  get(key) {
    try {
      const stored = MEMORY_STORE.get(`${this.namespace}:${key}`)
      return stored ?? null
    } catch {
      return null
    }
  }

  set(key, value) {
    try {
      MEMORY_STORE.set(`${this.namespace}:${key}`, value)
      return true
    } catch {
      return false
    }
  }

  remove(key) {
    MEMORY_STORE.delete(`${this.namespace}:${key}`)
  }

  clear() {
    for (const key of MEMORY_STORE.keys()) {
      if (key.startsWith(`${this.namespace}:`)) {
        MEMORY_STORE.delete(key)
      }
    }
  }

  keys() {
    return Array.from(MEMORY_STORE.keys())
      .filter(k => k.startsWith(`${this.namespace}:`))
      .map(k => k.slice(this.namespace.length + 1))
  }
}

export function createCrossPlatformStorage(options = {}) {
  return new CrossPlatformStorage(options)
}
