import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Whiteboard from '../../src/components/chat/Whiteboard'

describe('Whiteboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders whiteboard header', () => {
    render(<Whiteboard onSave={() => {}} onClose={() => {}} />)
    expect(screen.getByText('Whiteboard')).toBeDefined()
  })

  it('shows toolbar with color picker', () => {
    render(<Whiteboard onSave={() => {}} onClose={() => {}} />)
    expect(screen.getByRole('button', { name: /undo/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /redo/i })).toBeDefined()
    expect(screen.getByRole('button', { name: /clear/i })).toBeDefined()
  })

  it('calls onSave when save button clicked', () => {
    const onSave = vi.fn()
    render(<Whiteboard onSave={onSave} onClose={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /save/i }))
    expect(onSave).toHaveBeenCalled()
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<Whiteboard onSave={() => {}} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })
})
