import React from 'react'
import { render, screen } from '@testing-library/react'
import { Toggle } from '@/components/ui/toggle'

describe('Toggle', () => {
  it('renders toggle', () => {
    render(<Toggle>Toggle</Toggle>)
    expect(screen.getByText('Toggle')).toBeDefined()
  })

  it('applies variant', () => {
    render(<Toggle variant="outline">Outline</Toggle>)
    const toggle = screen.getByText('Outline')
    expect(toggle.className).toContain('border')
  })

  it('applies size', () => {
    render(<Toggle size="sm">Small</Toggle>)
    const toggle = screen.getByText('Small')
    expect(toggle.className).toContain('h-8')
  })

  it('is disabled when disabled prop is true', () => {
    render(<Toggle disabled>Disabled</Toggle>)
    const toggle = screen.getByText('Disabled')
    expect(toggle.hasAttribute('data-disabled')).toBe(true)
  })
})
