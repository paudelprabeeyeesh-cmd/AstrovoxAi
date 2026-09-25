import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MultiChatTabs from '../../src/components/workspace/MultiChatTabs'

describe('MultiChatTabs - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders single tab', () => {
    render(<MultiChatTabs conversations={[{ id: '1', title: 'Only' }]} activeId="1" onSelect={() => {}} />)
    expect(screen.getByText('Only')).toBeDefined()
  })

  it('handles empty conversations array', () => {
    render(<MultiChatTabs conversations={[]} activeId="" onSelect={() => {}} onNew={() => {}} />)
    expect(screen.getByRole('button', { name: /new chat tab/i })).toBeDefined()
  })

  it('handles many tabs', () => {
    const manyTabs = Array.from({ length: 50 }, (_, i) => ({ id: String(i), title: `Tab ${i}` }))
    render(<MultiChatTabs conversations={manyTabs} activeId="0" onSelect={() => {}} />)
    expect(screen.getByText('Tab 0')).toBeDefined()
    expect(screen.getByText('Tab 49')).toBeDefined()
  })
})
