import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TeamWorkspace from '../src/components/workspace/TeamWorkspace'

describe('TeamWorkspace', () => {
  const mockTeam = { id: '1', name: 'Acme Corp', plan: 'Pro' }
  const mockMembers = [
    { id: '1', name: 'Alice', email: 'alice@example.com', role: 'owner' },
    { id: '2', name: 'Bob', email: 'bob@example.com', role: 'admin' },
    { id: '3', name: 'Charlie', email: 'charlie@example.com', role: 'member' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders team name', () => {
    render(<TeamWorkspace team={mockTeam} members={mockMembers} />)
    expect(screen.getByText('Acme Corp')).toBeDefined()
  })

  it('renders member count', () => {
    render(<TeamWorkspace team={mockTeam} members={mockMembers} />)
    expect(screen.getByText('3 members')).toBeDefined()
  })

  it('renders all members', () => {
    render(<TeamWorkspace team={mockTeam} members={mockMembers} />)
    expect(screen.getByText('Alice')).toBeDefined()
    expect(screen.getByText('Bob')).toBeDefined()
    expect(screen.getByText('Charlie')).toBeDefined()
  })

  it('shows invite form when invite clicked', () => {
    render(<TeamWorkspace team={mockTeam} members={mockMembers} onInvite={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: /invite/i }))
    expect(screen.getByPlaceholderText(/colleague/i)).toBeDefined()
  })

  it('calls onInvite with email and role', () => {
    const onInvite = vi.fn()
    render(<TeamWorkspace team={mockTeam} members={mockMembers} onInvite={onInvite} />)
    fireEvent.click(screen.getByRole('button', { name: /invite/i }))
    fireEvent.change(screen.getByPlaceholderText(/colleague/i), { target: { value: 'new@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /send invite/i }))
    expect(onInvite).toHaveBeenCalledWith({ email: 'new@example.com', role: 'member', invitedAt: expect.any(String) })
  })
})
