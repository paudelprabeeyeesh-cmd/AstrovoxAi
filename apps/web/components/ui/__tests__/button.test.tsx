import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button', () => {
  it('renders with default variant', () => {
    render(<Button>Click me</Button>)
    const button = screen.getByRole('button')
    expect(button).toBeDefined()
    expect(button.textContent).toBe('Click me')
  })

  it('applies destructive variant', () => {
    render(<Button variant="destructive">Delete</Button>)
    const button = screen.getByRole('button')
    expect(button.className).toContain('bg-destructive')
  })

  it('applies outline variant', () => {
    render(<Button variant="outline">Outline</Button>)
    const button = screen.getByRole('button')
    expect(button.className).toContain('border')
  })

  it('applies size sm', () => {
    render(<Button size="sm">Small</Button>)
    const button = screen.getByRole('button')
    expect(button.className).toContain('h-8')
  })

  it('handles click events', () => {
    const onClick = jest.fn()
    render(<Button onClick={onClick}>Click</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>)
    const button = screen.getByRole('button')
    expect(button.hasAttribute('disabled')).toBe(true)
  })
})
