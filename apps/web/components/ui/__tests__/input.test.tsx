import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { Input } from '@/components/ui/input'

describe('Input', () => {
  it('renders input element', () => {
    render(<Input placeholder="Enter text" />)
    const input = screen.getByPlaceholderText('Enter text')
    expect(input).toBeDefined()
  })

  it('handles value changes', () => {
    const onChange = jest.fn()
    render(<Input onChange={onChange} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'test value' } })
    expect(onChange).toHaveBeenCalled()
  })

  it('is disabled when disabled prop is true', () => {
    render(<Input disabled />)
    const input = screen.getByRole('textbox')
    expect(input.hasAttribute('disabled')).toBe(true)
  })

  it('applies type attribute', () => {
    render(<Input type="email" />)
    const input = screen.getByRole('textbox')
    expect(input.getAttribute('type')).toBe('email')
  })
})
