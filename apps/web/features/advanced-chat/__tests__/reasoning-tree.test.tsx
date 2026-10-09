import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { ReasoningTree } from '../reasoning-tree'

const mockNodes = {
  root: { id: 'root', label: 'Root Question', type: 'root', children: ['step1'], status: 'completed', confidence: 0.9 },
  step1: { id: 'step1', label: 'Analyze data', type: 'step', children: ['leaf1'], status: 'completed', confidence: 0.85 },
  leaf1: { id: 'leaf1', label: 'Conclusion', type: 'leaf', status: 'completed', confidence: 0.8 },
}

describe('ReasoningTree', () => {
  it('renders root node', () => {
    render(<ReasoningTree nodes={mockNodes} rootId="root" />)
    expect(screen.getByText('Root Question')).toBeDefined()
  })

  it('expands on click', () => {
    render(<ReasoningTree nodes={mockNodes} rootId="root" />)
    expect(screen.queryByText('Analyze data')).toBeNull()
    fireEvent.click(screen.getByText('Root Question'))
    expect(screen.getByText('Analyze data')).toBeDefined()
  })

  it('shows confidence badge', () => {
    render(<ReasoningTree nodes={mockNodes} rootId="root" />)
    expect(screen.getByText('90%')).toBeDefined()
  })

  it('shows empty message when no root', () => {
    render(<ReasoningTree nodes={{}} />)
    expect(screen.getByText(/no reasoning data available/i)).toBeDefined()
  })
})
