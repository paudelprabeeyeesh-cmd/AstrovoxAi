import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { KnowledgeGraphView } from '../knowledge-graph-view'

const mockNodes = [
  { id: 'n1', label: 'Node A', type: 'entity' },
  { id: 'n2', label: 'Node B', type: 'entity' },
  { id: 'n3', label: 'Node C', type: 'entity' },
]

const mockEdges = [
  { source: 'n1', target: 'n2', label: 'related' },
  { source: 'n2', target: 'n3', label: 'connected' },
]

describe('KnowledgeGraphView', () => {
  it('renders nodes', () => {
    render(<KnowledgeGraphView nodes={mockNodes} edges={mockEdges} width={400} height={300} />)
    expect(screen.getByText('Node A')).toBeDefined()
  })

  it('filters nodes', () => {
    render(<KnowledgeGraphView nodes={mockNodes} edges={mockEdges} width={400} height={300} />)
    const input = screen.getByPlaceholderText(/filter nodes/i)
    fireEvent.change(input, { target: { value: 'Node A' } })
    expect(screen.getByText('Node A')).toBeDefined()
    expect(screen.queryByText('Node C')).toBeNull()
  })

  it('shows node count', () => {
    render(<KnowledgeGraphView nodes={mockNodes} edges={mockEdges} width={400} height={300} />)
    expect(screen.getByText('3 nodes')).toBeDefined()
  })
})
