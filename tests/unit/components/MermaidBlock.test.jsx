import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import MermaidBlock from '../../src/components/chat/MermaidBlock'

describe('MermaidBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(window as any).mermaid = {
      render: vi.fn().mockResolvedValue({ svg: '<svg>Diagram</svg>' })
    }
  })

  it('renders diagram on load', async () => {
    render(<MermaidBlock content="graph TD; A-->B;" />)
    await vi.waitFor(() => {
      expect((window as any).mermaid.render).toHaveBeenCalled()
    })
  })

  it('shows error on render failure', async () => {
    ;(window as any).mermaid = {
      render: vi.fn().mockRejectedValue(new Error('Syntax error'))
    }
    render(<MermaidBlock content="invalid mermaid" />)
    await vi.waitFor(() => {
      expect(screen.getByText(/diagram error/i)).toBeDefined()
    })
  })
})
