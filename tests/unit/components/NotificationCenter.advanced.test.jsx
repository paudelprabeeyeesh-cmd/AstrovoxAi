import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import NotificationCenter from '../../src/components/ui/NotificationCenter'

describe('NotificationCenter - Advanced', () => {
  const mockNotifications = [
    { id: '1', title: 'Info', message: 'Info message', type: 'info', timestamp: Date.now(), read: false },
    { id: '2', title: 'Warning', message: 'Warning message', type: 'warning', timestamp: Date.now(), read: false },
    { id: '3', title: 'Error', message: 'Error message', type: 'error', timestamp: Date.now(), read: false },
    { id: '4', title: 'Success', message: 'Success message', type: 'success', timestamp: Date.now(), read: true }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows unread count badge', () => {
    render(<NotificationCenter notifications={mockNotifications} />)
    expect(screen.getByText('3')).toBeDefined()
  })

  it('marks all as read', () => {
    render(<NotificationCenter notifications={mockNotifications} />)
    fireEvent.click(screen.getByRole('button', { name: /notifications/i }))
    fireEvent.click(screen.getByText('Mark all read'))
    expect(screen.queryByText('3')).toBeNull()
  })

  it('filters by type', () => {
    render(<NotificationCenter notifications={mockNotifications} />)
    fireEvent.click(screen.getByRole('button', { name: /notifications/i }))
    const filter = screen.getAllByRole('combobox')[0]
    fireEvent.change(filter, { target: { value: 'error' } })
    expect(screen.getByText('Error message')).toBeDefined()
    expect(screen.queryByText('Info message')).toBeNull()
  })
})
