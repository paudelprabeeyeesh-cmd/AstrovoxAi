import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useChatHistory } from '../../src/hooks/useChatHistory'

describe('useChatHistory - Advanced', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => null)
  })

  it('adds message to history', async () => {
    let hookResult: any
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
  })

  it('creates branch with label', async () => {
    let hookResult: any
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
    expect(hookResult.branches['msg-1'].label).toBe('Test Branch')
  })

  it('adds message to branch', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useChatHistory()
      return (
        <button onClick={() => { hookResult.createBranch('msg-1', 'Branch'); hookResult.addBranchMessage('msg-1', { content: 'branch msg' }) }}>
          Add Branch Msg
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(hookResult.branches['msg-1'].messages.length).toBe(1)
  })

  it('clears history', async () => {
    let hookResult: any
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
