import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import UsageDashboard from '../../src/components/dashboards/UsageDashboard'

describe('UsageDashboard', () => {
  const mockUsage = { current: 5000, limit: 10000, tokens: 50000, apiCalls: 1200 }
  const mockConversations = [
    { id: '1', title: 'Chat 1', userId: 'user-1', messageCount: 10 },
    { id: '2', title: 'Chat 2', userId: 'user-2', messageCount: 20 },
    { id: '3', title: 'Chat 3', userId: 'user-1', messageCount: 5 }
  ]
  const mockUsers = [
    { id: 'user-1', name: 'Alice', email: 'alice@example.com' },
    { id: 'user-2', name: 'Bob', email: 'bob@example.com' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders usage dashboard', () => {
    render(<UsageDashboard usage={mockUsage} conversations={mockConversations} users={mockUsers} />)
    expect(screen.getByText('Usage Dashboard')).toBeDefined()
  })

  it('shows usage statistics', () => {
    render(<UsageDashboard usage={mockUsage} conversations={mockConversations} users={mockUsers} />)
    expect(screen.getByText('3')).toBeDefined()
    expect(screen.getByText('35')).toBeDefined()
  })

  it('filters by user', () => {
    render(<UsageDashboard usage={mockUsage} conversations={mockConversations} users={mockUsers} />)
    const select = screen.getByRole('combobox', { name: /users/i })
    fireEvent.change(select, { target: { value: 'user-1' } })
    expect(screen.getByText('15')).toBeDefined()
  })
})
