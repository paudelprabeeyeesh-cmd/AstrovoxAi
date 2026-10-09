import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion'

describe('Accordion', () => {
  it('renders accordion items', () => {
    render(
      <Accordion type="single">
        <AccordionItem value="item-1">
          <AccordionTrigger>Section 1</AccordionTrigger>
          <AccordionContent>Content for section 1</AccordionContent>
        </AccordionItem>
      </Accordion>
    )
    expect(screen.getByText('Section 1')).toBeDefined()
    expect(screen.queryByText('Content for section 1')).toBeNull()
  })

  it('opens item on trigger click', () => {
    render(
      <Accordion type="single">
        <AccordionItem value="item-1">
          <AccordionTrigger>Section 1</AccordionTrigger>
          <AccordionContent>Content for section 1</AccordionContent>
        </AccordionItem>
      </Accordion>
    )
    fireEvent.click(screen.getByText('Section 1'))
    expect(screen.getByText('Content for section 1')).toBeDefined()
  })

  it('closes item on second click (single mode)', () => {
    render(
      <Accordion type="single">
        <AccordionItem value="item-1">
          <AccordionTrigger>Section 1</AccordionTrigger>
          <AccordionContent>Content for section 1</AccordionContent>
        </AccordionItem>
      </Accordion>
    )
    fireEvent.click(screen.getByText('Section 1'))
    expect(screen.getByText('Content for section 1')).toBeDefined()
    fireEvent.click(screen.getByText('Section 1'))
    expect(screen.queryByText('Content for section 1')).toBeNull()
  })

  it('allows multiple open items in multiple mode', () => {
    render(
      <Accordion type="multiple">
        <AccordionItem value="item-1">
          <AccordionTrigger>Section 1</AccordionTrigger>
          <AccordionContent>Content 1</AccordionContent>
        </AccordionItem>
        <AccordionItem value="item-2">
          <AccordionTrigger>Section 2</AccordionTrigger>
          <AccordionContent>Content 2</AccordionContent>
        </AccordionItem>
      </Accordion>
    )
    fireEvent.click(screen.getByText('Section 1'))
    fireEvent.click(screen.getByText('Section 2'))
    expect(screen.getByText('Content 1')).toBeDefined()
    expect(screen.getByText('Content 2')).toBeDefined()
  })
})
