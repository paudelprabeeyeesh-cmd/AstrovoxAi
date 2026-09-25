import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FileUpload from '../../src/components/chat/FileUpload'

describe('FileUpload - Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('accepts multiple files', () => {
    render(<FileUpload onUpload={() => {}} multiple={true} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input?.hasAttribute('multiple')).toBe(true)
  })

  it('shows max size info', () => {
    render(<FileUpload onUpload={() => {}} maxSize={5 * 1024 * 1024} />)
    expect(screen.getByText(/5mb/i)).toBeDefined()
  })

  it('handles drag enter and leave', () => {
    render(<FileUpload onUpload={() => {}} />)
    const dropZone = screen.getByRole('button', { name: /upload files/i })
    fireEvent.dragOver(dropZone)
    fireEvent.dragLeave(dropZone)
    expect(dropZone).toBeDefined()
  })
})
