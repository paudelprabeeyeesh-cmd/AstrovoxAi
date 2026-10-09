import React from 'react'
import { render, screen } from '@testing-library/react'
import { Breadcrumb } from '@/components/ui/breadcrumb'

describe('Breadcrumb', () => {
  it('renders breadcrumb items', () => {
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Products', href: '/products' },
          { label: 'Current' },
        ]}
      />
    )
    expect(screen.getByText('Home')).toBeDefined()
    expect(screen.getByText('Products')).toBeDefined()
    expect(screen.getByText('Current')).toBeDefined()
  })

  it('renders last item without link', () => {
    render(
      <Breadcrumb
        items={[
          { label: 'Home', href: '/' },
          { label: 'Current' },
        ]}
      />
    )
    const currentItem = screen.getByText('Current')
    expect(currentItem.closest('a')).toBeNull()
  })

  it('has aria-label', () => {
    render(<Breadcrumb items={[{ label: 'Home' }]} />)
    const nav = document.querySelector('nav[aria-label="Breadcrumb"]')
    expect(nav).toBeDefined()
  })
})
