import { describe, it, expect } from 'vitest'
import { PlatformType, StorageType, SyncStatus, PlatformEvent, SyncQueueItem } from '../../src/types/index'

describe('types', () => {
  it('PlatformType has expected values', () => {
    expect(PlatformType.WEB).toBe('web')
    expect(PlatformType.MOBILE).toBe('mobile')
    expect(PlatformType.DESKTOP).toBe('desktop')
    expect(PlatformType.EXTENSION).toBe('extension')
    expect(PlatformType.EDITOR).toBe('editor')
  })

  it('StorageType has expected values', () => {
    expect(StorageType.LOCAL_STORAGE).toBe('localStorage')
    expect(StorageType.INDEXED_DB).toBe('indexedDB')
    expect(StorageType.SUPABASE).toBe('supabase')
    expect(StorageType.FILE_SYSTEM).toBe('fileSystem')
  })

  it('SyncStatus has expected values', () => {
    expect(SyncStatus.PENDING).toBe('pending')
    expect(SyncStatus.SYNCING).toBe('syncing')
    expect(SyncStatus.SYNCED).toBe('synced')
    expect(SyncStatus.FAILED).toBe('failed')
  })

  it('PlatformEvent stores type and payload', () => {
    const event = new PlatformEvent('click', { target: 'button' })
    expect(event.type).toBe('click')
    expect(event.payload).toEqual({ target: 'button' })
    expect(event.timestamp).toBeGreaterThan(0)
  })

  it('PlatformEvent defaults payload to empty object', () => {
    const event = new PlatformEvent('load')
    expect(event.payload).toEqual({})
  })

  it('SyncQueueItem generates id and sets defaults', () => {
    const item = new SyncQueueItem('send', { text: 'hello' })
    expect(item.action).toBe('send')
    expect(item.data).toEqual({ text: 'hello' })
    expect(item.status).toBe(SyncStatus.PENDING)
    expect(item.retries).toBe(0)
    expect(item.id).toBeDefined()
    expect(item.createdAt).toBeDefined()
  })
})