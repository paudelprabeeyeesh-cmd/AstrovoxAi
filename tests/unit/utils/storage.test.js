import { describe, it, expect, beforeEach } from 'vitest'
import { StorageAdapter, createStorage } from '../../src/utils/storage'

describe('storage utils', () => {
  let storage

  beforeEach(() => {
    storage = createStorage('test')
    localStorage.clear()
  })

  it('get returns null for missing key', () => {
    expect(storage.get('missing')).toBeNull()
  })

  it('set and get round-trips values', () => {
    storage.set('key', { a: 1 })
    expect(storage.get('key')).toEqual({ a: 1 })
  })

  it('set returns true on success', () => {
    expect(storage.set('k', 1)).toBe(true)
  })

  it('remove deletes a key', () => {
    storage.set('k', 1)
    storage.remove('k')
    expect(storage.get('k')).toBeNull()
  })

  it('clear removes only namespaced keys', () => {
    storage.set('k1', 1)
    localStorage.setItem('other', JSON.stringify(2))
    storage.clear()
    expect(storage.get('k1')).toBeNull()
    expect(JSON.parse(localStorage.getItem('other'))).toBe(2)
  })

  it('keys returns only namespaced keys', () => {
    storage.set('a', 1)
    storage.set('b', 2)
    localStorage.setItem('other', 'x')
    const keys = storage.keys()
    expect(keys).toContain('a')
    expect(keys).toContain('b')
    expect(keys).not.toContain('other')
  })

  it('uses default namespace when none provided', () => {
    const defaultStorage = createStorage()
    defaultStorage.set('k', 1)
    expect(defaultStorage.get('k')).toBe(1)
  })

  it('handles invalid JSON gracefully', () => {
    localStorage.setItem('test:bad', 'not-json')
    expect(storage.get('bad')).toBeNull()
  })
})