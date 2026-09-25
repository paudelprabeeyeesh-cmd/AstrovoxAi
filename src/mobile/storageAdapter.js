import { Platform } from 'react-native'
import AsyncStorage from '@react-native-async-storage/async-storage'
import * as SecureStore from 'expo-secure-store'

export function createRNStorage(namespace = 'astrovox') {
  const prefix = `@astrovox:${namespace}:`

  return {
    async get(key) {
      try {
        const value = await AsyncStorage.getItem(prefix + key)
        if (value === null) return null
        return JSON.parse(value)
      } catch (e) {
        console.error(`RNStorage get error [${key}]:`, e)
        return null
      }
    },

    async set(key, value) {
      try {
        await AsyncStorage.setItem(prefix + key, JSON.stringify(value))
        return true
      } catch (e) {
        console.error(`RNStorage set error [${key}]:`, e)
        return false
      }
    },

    async remove(key) {
      try {
        await AsyncStorage.removeItem(prefix + key)
      } catch (e) {
        console.error(`RNStorage remove error [${key}]:`, e)
      }
    },

    async clear() {
      try {
        const keys = await AsyncStorage.getAllKeys()
        const prefixKeys = keys.filter(k => k.startsWith(prefix))
        if (prefixKeys.length > 0) {
          await AsyncStorage.multiRemove(prefixKeys)
        }
      } catch (e) {
        console.error('RNStorage clear error:', e)
      }
    },

    async keys() {
      try {
        const keys = await AsyncStorage.getAllKeys()
        return keys
          .filter(k => k.startsWith(prefix))
          .map(k => k.slice(prefix.length))
      } catch (e) {
        console.error('RNStorage keys error:', e)
        return []
      }
    }
  }
}

export function createSecureStorage(namespace = 'astrovox') {
  const prefix = `astrovox:${namespace}:`

  return {
    async get(key) {
      try {
        if (Platform.OS === 'web') {
          const value = localStorage.getItem(prefix + key)
          return value ? JSON.parse(value) : null
        }
        const value = await SecureStore.getItemAsync(prefix + key)
        if (value === null) return null
        return JSON.parse(value)
      } catch (e) {
        console.error(`SecureStorage get error [${key}]:`, e)
        return null
      }
    },

    async set(key, value) {
      try {
        const serialized = JSON.stringify(value)
        if (Platform.OS === 'web') {
          localStorage.setItem(prefix + key, serialized)
        } else {
          await SecureStore.setItemAsync(prefix + key, serialized)
        }
        return true
      } catch (e) {
        console.error(`SecureStorage set error [${key}]:`, e)
        return false
      }
    },

    async remove(key) {
      try {
        if (Platform.OS === 'web') {
          localStorage.removeItem(prefix + key)
        } else {
          await SecureStore.deleteItemAsync(prefix + key)
        }
      } catch (e) {
        console.error(`SecureStorage remove error [${key}]:`, e)
      }
    },

    async isAvailable() {
      try {
        if (Platform.OS === 'web') return true
        return await SecureStore.isAvailableAsync()
      } catch {
        return false
      }
    }
  }
}

export function createMemoryStorage() {
  const store = new Map()

  return {
    get(key) {
      const item = store.get(key)
      if (item && item.expiry && Date.now() > item.expiry) {
        store.delete(key)
        return null
      }
      return item?.value ?? null
    },

    set(key, value, ttlMs) {
      store.set(key, {
        value,
        expiry: ttlMs ? Date.now() + ttlMs : null
      })
    },

    remove(key) {
      store.delete(key)
    },

    clear() {
      store.clear()
    },

    keys() {
      return Array.from(store.keys())
    }
  }
}
