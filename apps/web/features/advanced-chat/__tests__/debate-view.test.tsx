import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { DebateView } from '../debate-view'

const mockPerspectives = [
  {
    id: 'p1',
    name: 'Optimist',
    stance: 'The plan will succeed',
    arguments: ['Low risk', 'High reward'],
    evidence: ['Past success'],
  },
  {
    id: 'p2',
    name: 'Skeptic',
    stance: 'The plan may fail',
    arguments: ['Unknown variables', 'Budget concerns'],
    evidence: ['Industry data'],
  },
]

describe('DebateView', () => {
  it('renders perspectives', () => {
    render(<DebateView perspectives={mockPerspectives} />)
    expect(screen.getByText('Optimist')).toBeDefined()
    expect(screen.getByText('Skeptic')).toBeDefined()
  })

  it('shows perspective count badge', () => {
    render(<DebateView perspectives={mockPerspectives} />)
    expect(screen.getByText('2 perspectives')).toBeDefined()
  })

  it('expands perspective on click', () => {
    render(<DebateView perspectives={mockPerspectives} />)
    fireEvent.click(screen.getByText('Optimist'))
    expect(screen.getByText('The plan will succeed')).toBeDefined()
  })

  it('shows synthesis when provided', () => {
    render(<DebateView perspectives={mockPerspectives} synthesis="Balanced approach recommended." />)
    expect(screen.getByText('Balanced approach recommended.')).toBeDefined()
  })

  it('shows empty state when no perspectives', () => {
    render(<DebateView perspectives={[]} />)
    expect(screen.getByText(/no perspectives available/i)).toBeDefined()
  })
})
