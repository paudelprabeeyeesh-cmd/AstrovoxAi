import React from 'react'
import { render, screen } from '@testing-library/react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

describe('Card', () => {
  it('renders card with children', () => {
    render(<Card>Card content</Card>)
    const card = screen.getByText('Card content')
    expect(card).toBeDefined()
  })

  it('renders card header', () => {
    render(<CardHeader>Header</CardHeader>)
    expect(screen.getByText('Header')).toBeDefined()
  })

  it('renders card title', () => {
    render(<CardTitle>Title</CardTitle>)
    const title = screen.getByText('Title')
    expect(title.tagName).toBe('H3')
  })

  it('renders card description', () => {
    render(<CardDescription>Description</CardDescription>)
    expect(screen.getByText('Description')).toBeDefined()
  })

  it('renders card content', () => {
    render(<CardContent>Content</CardContent>)
    expect(screen.getByText('Content')).toBeDefined()
  })

  it('renders card footer', () => {
    render(<CardFooter>Footer</CardFooter>)
    expect(screen.getByText('Footer')).toBeDefined()
  })
})
