import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useBackgroundSync } from '../../../sync/BackgroundSync'

describe('BackgroundSync', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.getItem = vi.fn(() => null)
    localStorage.setItem = vi.fn()
    vi.spyOn(window, 'addEventListener').mockImplementation(() => {})
  })

  it('adds item to sync queue', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useBackgroundSync()
      return (
        <button onClick={() => hookResult.addToSyncQueue({ type: 'message', data: 'test' })}>
          Sync
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(localStorage.setItem).toHaveBeenCalled()
  })

  it('starts in idle state', () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useBackgroundSync()
      return <div>Test</div>
    }
    render(<TestComponent />)
    expect(hookResult.syncStatus).toBe('idle')
  })

  it('resolves conflicts', async () => {
    let hookResult: any
    function TestComponent() {
      hookResult = useBackgroundSync()
      return (
        <button onClick={() => hookResult.resolveConflict('conflict-1', 'local')}>
          Resolve
        </button>
      )
    }
    render(<TestComponent />)
    fireEvent.click(screen.getByRole('button'))
    expect(localStorage.setItem).toHaveBeenCalled()
  })
})
