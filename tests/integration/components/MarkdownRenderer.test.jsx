import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import MarkdownRenderer from '../src/components/chat/MarkdownRenderer'

describe('MarkdownRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders plain text', () => {
    render(<MarkdownRenderer content="Hello world" />)
    expect(screen.getByText('Hello world')).toBeDefined()
  })

  it('renders code blocks', () => {
    render(<MarkdownRenderer content={'```javascript\nconst x = 1;\n```'} />)
    expect(screen.getByText('javascript')).toBeDefined()
    expect(screen.getByText('const x = 1;')).toBeDefined()
  })

  it('copies all content', async () => {
    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText: mockWriteText } })

    render(<MarkdownRenderer content="Test content" />)
    const copyButton = screen.getByRole('button', { name: /copy all content/i })
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(mockWriteText).toHaveBeenCalledWith('Test content')
    })
  })

  it('renders images', () => {
    render(<MarkdownRenderer content={'![Alt text](https://example.com/image.png)'} />)
    const img = screen.getByRole('img')
    expect(img).toBeDefined()
    expect(img.getAttribute('alt')).toBe('Alt text')
  })
})
