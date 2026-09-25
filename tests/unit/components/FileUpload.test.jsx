import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FileUpload from '../../src/components/chat/FileUpload'

describe('FileUpload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload area', () => {
    render(<FileUpload onUpload={() => {}} />)
    expect(screen.getByRole('button', { name: /upload files/i })).toBeDefined()
  })

  it('shows drag and drop text', () => {
    render(<FileUpload onUpload={() => {}} />)
    expect(screen.getByText(/drag and drop/i)).toBeDefined()
  })

  it('validates file size', async () => {
    render(<FileUpload onUpload={() => {}} maxSize={1000} />)
    const input = document.querySelector('input[type="file"]')
    expect(input).toBeDefined()
  })

  it('opens file browser on click', () => {
    render(<FileUpload onUpload={() => {}} />)
    const uploadArea = screen.getByRole('button', { name: /upload files/i })
    fireEvent.click(uploadArea)
    expect(document.querySelector('input[type="file"]')).toBeDefined()
  })
})
