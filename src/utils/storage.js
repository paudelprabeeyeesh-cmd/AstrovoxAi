export class StorageAdapter {
  constructor(namespace = 'astrovox') {
    this.namespace = namespace
    this.prefix = `${namespace}:`
  }

  get(key) {
    try {
      const item = localStorage.getItem(this.prefix + key)
      return item ? JSON.parse(item) : null
    } catch {
      return null
    }
  }

  set(key, value) {
    try {
      localStorage.setItem(this.prefix + key, JSON.stringify(value))
      return true
    } catch {
      return false
    }
  }

  remove(key) {
    localStorage.removeItem(this.prefix + key)
  }

  clear() {
    const keys = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key?.startsWith(this.prefix)) {
        keys.push(key)
      }
    }
    keys.forEach(k => localStorage.removeItem(k))
  }

  keys() {
    const keys = []
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key?.startsWith(this.prefix)) {
        keys.push(key.slice(this.prefix.length))
      }
    }
    return keys
  }
}

export function createStorage(namespace) {
  return new StorageAdapter(namespace)
}
