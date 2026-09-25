import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import CustomerAdmin from '../src/components/admin/CustomerAdmin'

describe('CustomerAdmin', () => {
  const mockOrg = { id: '1', name: 'Acme Corp', plan: 'Pro' }
  const mockMembers = [
    { id: '1', name: 'Alice', email: 'alice@example.com', role: 'owner' },
    { id: '2', name: 'Bob', email: 'bob@example.com', role: 'member' }
  ]
  const mockUsage = { current: 5000, limit: 10000, tokens: 50000, apiCalls: 1200 }
  const mockBilling = { currentPlan: 'Pro', nextBilling: '2025-02-01', amount: '$49.99' }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders organization name', () => {
    render(<CustomerAdmin organization={mockOrg} members={mockMembers} usage={mockUsage} billing={mockBilling} />)
    expect(screen.getByText('Acme Corp')).toBeDefined()
  })

  it('renders usage overview', () => {
    render(<CustomerAdmin organization={mockOrg} members={mockMembers} usage={mockUsage} billing={mockBilling} />)
    expect(screen.getByText('5,000')).toBeDefined()
    expect(screen.getByText('10,000')).toBeDefined()
  })

  it('shows upgrade plan button', () => {
    render(<CustomerAdmin organization={mockOrg} members={mockMembers} usage={mockUsage} billing={mockBilling} />)
    expect(screen.getByRole('button', { name: /upgrade plan/i })).toBeDefined()
  })

  it('opens upgrade panel', () => {
    render(<CustomerAdmin organization={mockOrg} members={mockMembers} usage={mockUsage} billing={mockBilling} />)
    fireEvent.click(screen.getByRole('button', { name: /upgrade plan/i }))
    expect(screen.getByText('Available Plans')).toBeDefined()
  })

  it('shows team members', () => {
    render(<CustomerAdmin organization={mockOrg} members={mockMembers} usage={mockUsage} billing={mockBilling} />)
    expect(screen.getByText('Alice')).toBeDefined()
    expect(screen.getByText('Bob')).toBeDefined()
  })
})
