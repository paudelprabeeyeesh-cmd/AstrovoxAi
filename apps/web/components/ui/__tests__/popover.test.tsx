import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'

describe('Popover', () => {
  it('renders popover with trigger', () => {
    render(
      <Popover>
        <PopoverTrigger>Open</PopoverTrigger>
        <PopoverContent>Content</PopoverContent>
      </Popover>
    )
    expect(screen.getByText('Open')).toBeDefined()
  })

  it('shows content on trigger click', () => {
    render(
      <Popover>
        <PopoverTrigger>Open</PopoverTrigger>
        <PopoverContent>Popover Content</PopoverContent>
      </Popover>
    )
    fireEvent.click(screen.getByText('Open'))
    expect(screen.getByText('Popover Content')).toBeDefined()
  })
})
