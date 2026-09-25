import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useChatHistory } from '../../src/hooks/useChatHistory'

describe('useChatHistory - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => null)
  })

  it('handles empty content', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useChatHistory()
      return (
        <button onClick={() => hookResult.addMessage({ content: '' })}>
          Add
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(hookResult.history.length).toBe(1)
    expect(hookResult.history[0].content).toBe('')
  })

  it('generates unique IDs', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useChatHistory()
      return (
        <button onClick={() => { hookResult.addMessage({ content: 'a' }); hookResult.addMessage({ content: 'b' }) }}>
          Add
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(hookResult.history[0].id).not.toBe(hookResult.history[1].id)
  })

  it('handles rapid additions', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useChatHistory()
      return (
        <button onClick={() => {
          for (let i = 0; i < 10; i++) {
            hookResult.addMessage({ content: `msg-${i}` })
          }
        }}>
          Add
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(hookResult.history.length).toBe(10)
  })
})
