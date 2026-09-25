import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CodeExecution from '../../src/components/CodeExecution'

describe('CodeExecution', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('renders code editor', () => {
    render(<CodeExecution onExecute={() => {}} onClose={() => {}} />)
    expect(screen.getByPlaceholderText(/write.*code/i)).toBeDefined()
  })

  it('shows language selector', () => {
    render(<CodeExecution onExecute={() => {}} onClose={() => {}} />)
    expect(screen.getByRole('combobox')).toBeDefined()
  })

  it('executes code when run is clicked', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ output: 'Hello World' })
    })

    render(<CodeExecution onExecute={() => {}} onClose={() => {}} />)
    const textarea = screen.getByPlaceholderText(/write.*code/i)
    await userEvent.type(textarea, 'print("Hello World")')

    await userEvent.click(screen.getByRole('button', { name: /run/i }))
    expect(fetch).toHaveBeenCalledWith(
      '/api/code/execute',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('print("Hello World")')
      })
    )
  })

  it('displays execution output', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ output: 'Execution successful' })
    })

    render(<CodeExecution onExecute={() => {}} onClose={() => {}} />)
    const textarea = screen.getByPlaceholderText(/write.*code/i)
    await userEvent.type(textarea, '1 + 1')

    await userEvent.click(screen.getByRole('button', { name: /run/i }))
    await waitFor(() => {
      expect(screen.getByText('Execution successful')).toBeDefined()
    })
  })

  it('displays error on failed execution', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error'
    })

    render(<CodeExecution onExecute={() => {}} onClose={() => {}} />)
    const textarea = screen.getByPlaceholderText(/write.*code/i)
    await userEvent.type(textarea, 'invalid code')

    await userEvent.click(screen.getByRole('button', { name: /run/i }))
    await waitFor(() => {
      expect(screen.getByText(/execution failed/i)).toBeDefined()
    })
  })

  it('calls onClose when close button is clicked', async () => {
    const onClose = vi.fn()
    render(<CodeExecution onExecute={() => {}} onClose={onClose} />)
    await userEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('disables run button when code is empty', () => {
    render(<CodeExecution onExecute={() => {}} onClose={() => {}} />)
    const runButton = screen.getByRole('button', { name: /run/i })
    expect(runButton).toBeDisabled()
  })

  it('supports keyboard shortcut Ctrl+Enter', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ output: 'Shortcut result' })
    })

    render(<CodeExecution onExecute={() => {}} onClose={() => {}} />)
    const textarea = screen.getByPlaceholderText(/write.*code/i)
    await userEvent.type(textarea, '1 + 1')

    textarea.focus()
    await userEvent.keyboard('{Control>}+{Enter}')
    expect(fetch).toHaveBeenCalled()
  })
})
