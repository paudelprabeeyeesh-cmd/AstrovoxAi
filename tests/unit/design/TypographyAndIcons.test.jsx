import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { Icon } from '../src/design/Iconography'
import { TYPOGRAPHY, useTypography } from '../src/design/TypographyScale'

describe('TypographyScale', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('has all scale sizes', () => {
    const sizes = ['xs', 'sm', 'base', 'md', 'lg', 'xl', '2xl', '3xl', '4xl']
    for (const size of sizes) {
      expect(TYPOGRAPHY.scale[size]).toBeDefined()
      expect(TYPOGRAPHY.scale[size].fontSize).toBeDefined()
      expect(TYPOGRAPHY.scale[size].lineHeight).toBeDefined()
    }
  })

  it('has all font weights', () => {
    const weights = ['normal', 'medium', 'semibold', 'bold', 'black']
    for (const weight of weights) {
      expect(TYPOGRAPHY.weights[weight]).toBeDefined()
    }
  })

  it('has all font families', () => {
    expect(TYPOGRAPHY.families.sans).toBeDefined()
    expect(TYPOGRAPHY.families.mono).toBeDefined()
    expect(TYPOGRAPHY.families.display).toBeDefined()
  })
})

describe('Iconography', () => {
  it('renders icon by name', () => {
    render(<Icon name="chat" size={20} />)
    expect(screen.getByLabelText(/chat/i)).toBeDefined()
  })

  it('renders different icon sizes', () => {
    const { container } = render(<Icon name="send" size={32} />)
    const svg = container.querySelector('svg')
    expect(svg).toHaveAttribute('width', '32')
    expect(svg).toHaveAttribute('height', '32')
  })
})
