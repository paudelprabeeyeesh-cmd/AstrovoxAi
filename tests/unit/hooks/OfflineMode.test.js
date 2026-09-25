import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useOfflineMode } from '../../offline/OfflineManager'

describe('OfflineMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => null)
    localStorage.setItem = vi.fn()
    localStorage.removeItem = vi.fn()
  })

  it('detects online status', () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useOfflineMode()
      return <div>Test</div>
    }
    render(<TestComponent />)
    expect(hookResult.isOnline).toBe(navigator.onLine)
  })

  it('saves message offline', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useOfflineMode()
      return (
        <button onClick={() => hookResult.saveMessageOffline({ content: 'test' })}>
          Save
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(localStorage.setItem).toHaveBeenCalled()
  })

  it('clears offline data', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useOfflineMode()
      return (
        <button onClick={hookResult.clearOfflineData}>
          Clear
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(localStorage.removeItem).toHaveBeenCalled()
  })
})
