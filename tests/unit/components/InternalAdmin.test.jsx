import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import InternalAdmin from '../src/components/admin/InternalAdmin'

describe('InternalAdmin', () => {
  const mockUsers = [
    { id: '1', name: 'Alice', email: 'alice@example.com', role: 'admin', status: 'active', createdAt: '2025-01-01' },
    { id: '2', name: 'Bob', email: 'bob@example.com', role: 'user', status: 'active', createdAt: '2025-01-02' },
    { id: '3', name: 'Charlie', email: 'charlie@example.com', role: 'user', status: 'suspended', createdAt: '2025-01-03' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders admin panel', () => {
    render(<InternalAdmin users={mockUsers} conversations={[]} metrics={{}} />)
    expect(screen.getByText('Internal Admin Panel')).toBeDefined()
  })

  it('renders user table', () => {
    render(<InternalAdmin users={mockUsers} conversations={[]} metrics={{}} />)
    expect(screen.getByText('Alice')).toBeDefined()
    expect(screen.getByText('Bob')).toBeDefined()
    expect(screen.getByText('Charlie')).toBeDefined()
  })

  it('filters users by search', () => {
    render(<InternalAdmin users={mockUsers} conversations={[]} metrics={{}} />)
    const searchInput = screen.getByPlaceholderText(/search users/i)
    fireEvent.change(searchInput, { target: { value: 'Alice' } })
    expect(screen.getByText('Alice')).toBeDefined()
    expect(screen.queryByText('Bob')).toBeNull()
  })

  it('shows system tab', () => {
    render(<InternalAdmin users={mockUsers} conversations={[]} metrics={{}} />)
    fireEvent.click(screen.getByRole('tab', { name: /system/i }))
    expect(screen.getByText('CPU Usage')).toBeDefined()
  })

  it('shows logs tab', () => {
    render(<InternalAdmin users={mockUsers} conversations={[]} metrics={{}} />)
    fireEvent.click(screen.getByRole('tab', { name: /logs/i }))
    expect(screen.getByText(/system initialized/i)).toBeDefined()
  })
})
