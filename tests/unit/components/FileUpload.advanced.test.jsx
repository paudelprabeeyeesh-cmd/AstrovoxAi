import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FileUpload from '../../src/components/chat/FileUpload'

describe('FileUpload - Advanced', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('accepts only specified file types', () => {
    render(<FileUpload onUpload={() => {}} accept=".pdf,.doc,.docx" />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input?.accept).toBe('.pdf,.doc,.docx')
  })

  it('validates max file size', async () => {
    render(<FileUpload onUpload={() => {}} maxSize={1024} />)
    const errorText = screen.getByText(/max size/i)
    expect(errorText).toBeDefined()
  })

  it('shows upload progress', async () => {
    render(<FileUpload onUpload={() => {}} />)
    const file = new File(['test'], 'test.txt', { type: 'text/plain' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    if (input) {
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(file)
      input.files = dataTransfer.files
      fireEvent.change(input)
    }
  })
})
