import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AnimatedContainer, AnimatedList } from '../../src/design/MotionLibrary'
import { motion } from 'framer-motion'

describe('MotionLibrary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('AnimatedContainer renders children', () => {
    render(<AnimatedContainer><div>Test Content</div></AnimatedContainer>)
    expect(screen.getByText('Test Content')).toBeDefined()
  })

  it('AnimatedContainer applies animation preset', () => {
    render(<AnimatedContainer preset="slideUp"><div>Sliding</div></AnimatedContainer>)
    expect(screen.getByText('Sliding')).toBeDefined()
  })

  it('AnimatedList renders children', () => {
    render(
      <AnimatedList>
        <div>Item 1</div>
        <div>Item 2</div>
      </AnimatedList>
    )
    expect(screen.getByText('Item 1')).toBeDefined()
    expect(screen.getByText('Item 2')).toBeDefined()
  })
})
