import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from '@/components/ui/command'

describe('Command', () => {
  it('renders command input', () => {
    render(
      <Command>
        <CommandInput placeholder="Search..." />
      </Command>
    )
    expect(screen.getByPlaceholderText('Search...')).toBeDefined()
  })

  it('renders command groups and items', () => {
    render(
      <Command>
        <CommandList>
          <CommandGroup heading="Suggestions">
            <CommandItem value="calendar">Calendar</CommandItem>
            <CommandItem value="search">Search</CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    )
    expect(screen.getByText('Suggestions')).toBeDefined()
    expect(screen.getByText('Calendar')).toBeDefined()
    expect(screen.getByText('Search')).toBeDefined()
  })

  it('renders empty state', () => {
    render(
      <Command>
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
        </CommandList>
      </Command>
    )
    expect(screen.getByText('No results found.')).toBeDefined()
  })

  it('handles item selection', () => {
    const onSelect = jest.fn()
    render(
      <Command>
        <CommandList>
          <CommandGroup>
            <CommandItem value="test-item" onSelect={onSelect}>Test Item</CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    )
    fireEvent.click(screen.getByText('Test Item'))
    expect(onSelect).toHaveBeenCalledWith('test-item')
  })

  it('does not select disabled items', () => {
    const onSelect = jest.fn()
    render(
      <Command>
        <CommandList>
          <CommandGroup>
            <CommandItem value="test-item" onSelect={onSelect} disabled>Disabled Item</CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    )
    fireEvent.click(screen.getByText('Disabled Item'))
    expect(onSelect).not.toHaveBeenCalled()
  })
})
