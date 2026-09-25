import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import CodeBlock from '../../src/components/chat/CodeBlock'

describe('CodeBlock', () => {
  it('renders code content', () => {
    render(<CodeBlock language="javascript" value="const x = 1;" />)
    expect(screen.getByText('const x = 1;')).toBeDefined()
  })

  it('shows language label', () => {
    render(<CodeBlock language="python" value="print('hello')" />)
    expect(screen.getByText('python')).toBeDefined()
  })

  it('copies code on button click', async () => {
    const mockWriteText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText: mockWriteText } })

    render(<CodeBlock language="js" value="test" />)
    const copyButton = screen.getByRole('button', { name: /copy code/i })
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(mockWriteText).toHaveBeenCalledWith('test')
    })
    expect(screen.getByText('Copied')).toBeDefined()
  })
})
