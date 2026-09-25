import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TeamWorkspace from '../../src/components/workspace/TeamWorkspace'

describe('TeamWorkspace - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('handles empty members list', () => {
    render(<TeamWorkspace team={{ id: '1', name: 'Team' }} members={[]} />)
    expect(screen.getByText('0 members')).toBeDefined()
  })

  it('handles large team', () => {
    const manyMembers = Array.from({ length: 100 }, (_, i) => ({
      id: String(i),
      name: `User ${i}`,
      email: `user${i}@example.com`,
      role: 'member'
    }))
    render(<TeamWorkspace team={{ id: '1', name: 'Team' }} members={manyMembers} />)
    expect(screen.getByText('User 0')).toBeDefined()
    expect(screen.getByText('99 members')).toBeDefined()
  })

  it('handles missing team data', () => {
    render(<TeamWorkspace team={null} members={[]} />)
    expect(screen.getByText('Team Workspace')).toBeDefined()
  })
})
