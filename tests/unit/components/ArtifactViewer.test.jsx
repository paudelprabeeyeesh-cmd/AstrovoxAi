import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ArtifactViewer from '../../src/components/chat/ArtifactViewer'

describe('ArtifactViewer', () => {
  const mockArtifact = {
    type: 'code',
    title: 'Example Code',
    language: 'javascript',
    content: 'const x = 1;\nconsole.log(x);'
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders artifact header', () => {
    render(<ArtifactViewer artifact={mockArtifact} />)
    expect(screen.getByText('Example Code')).toBeDefined()
  })

  it('shows artifact type badge', () => {
    render(<ArtifactViewer artifact={mockArtifact} />)
    expect(screen.getByText('code')).toBeDefined()
  })

  it('expands artifact on click', () => {
    render(<ArtifactViewer artifact={mockArtifact} />)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByText('const x = 1;')).toBeDefined()
  })

  it('renders nothing without artifact', () => {
    const { container } = render(<ArtifactViewer artifact={null} />)
    expect(container.firstChild).toBeNull()
  })
})
