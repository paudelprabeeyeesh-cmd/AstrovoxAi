import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useChatHistory } from '../src/hooks/useChatHistory'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('useChatHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.getItem.mockReturnValue(null)
  })

  it('initializes with empty state', () => {
    let hookResult
    function TestComponent() {
      hookResult = useChatHistory()
      return null
    }
    render(<TestComponent />)
    expect(hookResult.history).toEqual([])
    expect(hookResult.branches).toEqual({})
  })

  it('adds message to history', async () => {
    let hookResult
    function TestComponent() {
      hookResult = useChatHistory()
      return (
        <button onClick={() => hookResult.addMessage({ content: 'test' })}>
          Add
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(hookResult.history.length).toBe(1)
    expect(hookResult.history[0].content).toBe('test')
  })

  it('creates branch', async () => {
    let hookResult
    function TestComponent() {
      hookResult = useChatHistory()
      return (
        <button onClick={() => hookResult.createBranch('msg-1', 'Test Branch')}>
          Branch
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(Object.keys(hookResult.branches).length).toBe(1)
  })

  it('clears history', async () => {
    let hookResult
    function TestComponent() {
      hookResult = useChatHistory()
      return (
        <button onClick={() => { hookResult.addMessage({ content: 'test' }); hookResult.clearHistory() }}>
          Clear
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(hookResult.history).toEqual([])
  })
})
