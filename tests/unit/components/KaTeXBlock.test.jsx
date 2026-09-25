import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import KaTeXBlock from '../../src/components/chat/KaTeXBlock'

describe('KaTeXBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders math content', async () => {
    render(<KaTeXBlock content="x^2" display={true} />)
    await vi.waitFor(() => {
      expect(screen.getByText(/x\^2/)).toBeDefined()
    })
  })

  it('shows error on render failure', async () => {
    ;(window as any).katex = {
      render: vi.fn().mockImplementation(() => { throw new Error('Invalid math') })
    }
    render(<KaTeXBlock content="invalid" display={true} />)
    await vi.waitFor(() => {
      expect(screen.getByText(/math render error/i)).toBeDefined()
    })
  })
})
