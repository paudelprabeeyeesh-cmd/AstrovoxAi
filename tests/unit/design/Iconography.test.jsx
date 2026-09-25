import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Icon } from '../src/design/Iconography'

describe('Iconography', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders chat icon', () => {
    render(<Icon name="chat" size={20} />)
    const svg = document.querySelector('svg')
    expect(svg).toBeDefined()
  })

  it('renders different icons', () => {
    const icons = ['send', 'copy', 'edit', 'trash', 'settings', 'bell', 'user', 'code', 'mic', 'camera']
    for (const icon of icons) {
      render(<Icon name={icon} size={20} />)
      expect(document.querySelector('svg')).toBeDefined()
    }
  })

  it('applies correct size', () => {
    render(<Icon name="chat" size={32} />)
    const svg = document.querySelector('svg')
    expect(svg).toHaveAttribute('width', '32')
    expect(svg).toHaveAttribute('height', '32')
  })

  it('applies custom className', () => {
    const { container } = render(<Icon name="chat" size={20} className="custom-class" />)
    expect(container.firstChild).toHaveClass('custom-class')
  })
})
