import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import NotificationCenter from '../../src/components/ui/NotificationCenter'

describe('NotificationCenter', () => {
  const mockNotifications = [
    { id: '1', title: 'Test', message: 'Test message', type: 'info', timestamp: Date.now(), read: false },
    { id: '2', title: 'Warning', message: 'Warning message', type: 'warning', timestamp: Date.now(), read: false },
    { id: '3', title: 'Old', message: 'Old message', type: 'info', timestamp: Date.now() - 86400000, read: true }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders notification button', () => {
    render(<NotificationCenter notifications={mockNotifications} />)
    expect(screen.getByRole('button', { name: /notifications/i })).toBeDefined()
  })

  it('shows unread count', () => {
    render(<NotificationCenter notifications={mockNotifications} />)
    expect(screen.getByText('2')).toBeDefined()
  })

  it('opens notification panel on click', () => {
    render(<NotificationCenter notifications={mockNotifications} />)
    fireEvent.click(screen.getByRole('button', { name: /notifications/i }))
    expect(screen.getByText('Mark all read')).toBeDefined()
  })

  it('filters notifications', () => {
    render(<NotificationCenter notifications={mockNotifications} />)
    fireEvent.click(screen.getByRole('button', { name: /notifications/i }))
    const filter = screen.getByRole('combobox')
    fireEvent.change(filter, { target: { value: 'unread' } })
    expect(screen.getByText('Test')).toBeDefined()
    expect(screen.queryByText('Old')).toBeNull()
  })
})
