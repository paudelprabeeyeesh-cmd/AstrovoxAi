import React from 'react'
import { renderHook, act } from '@testing-library/react'
import { useLocalStorage } from '@/hooks/use-local-storage'

describe('useLocalStorage', () => {
  const mockLocalStorage = (() => {
    let store: Record<string, string> = {}
    return {
      getItem: (key: string) => store[key] || null,
      setItem: (key: string, value: string) => {
        store[key] = value
      },
      removeItem: (key: string) => {
        delete store[key]
      },
      clear: () => {
        store = {}
      },
    }
  })()

  Object.defineProperty(window, 'localStorage', {
    value: mockLocalStorage,
  })

  beforeEach(() => {
    mockLocalStorage.clear()
  })

  it('returns initial value when no stored value exists', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    expect(result.current[0]).toBe('initial')
  })

  it('returns stored value when it exists', () => {
    mockLocalStorage.setItem('test-key', JSON.stringify('stored'))
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    expect(result.current[0]).toBe('stored')
  })

  it('updates stored value', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    act(() => {
      result.current[1]('updated')
    })
    expect(result.current[0]).toBe('updated')
    expect(mockLocalStorage.getItem('test-key')).toBe(JSON.stringify('updated'))
  })

  it('supports functional updates', () => {
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    act(() => {
      result.current[1]((prev) => `${prev}-updated`)
    })
    expect(result.current[0]).toBe('initial-updated')
  })
})
