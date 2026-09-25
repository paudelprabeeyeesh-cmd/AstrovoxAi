import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Search from '../../src/components/Search'

describe('Search', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  it('renders search input', () => {
    render(<Search onResultSelect={() => {}} />)
    expect(screen.getByPlaceholderText(/search/i)).toBeDefined()
  })

  it('shows loading state while searching', async () => {
    let resolveFetch
    global.fetch = vi.fn(() => new Promise((resolve) => {
      resolveFetch = resolve
    }))

    render(<Search onResultSelect={() => {}} />)
    const input = screen.getByPlaceholderText(/search/i)
    await userEvent.type(input, 'test query')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /clear/i })).toBeDefined()
    })

    resolveFetch({
      ok: true,
      json: () => Promise.resolve({ results: [] })
    })

    await waitFor(() => {
      expect(fetch).toHaveBeenCalled()
    })
  })

  it('displays search results', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        results: [
          { id: '1', title: 'Test Result', snippet: 'This is a test result', type: 'conversation' }
        ]
      })
    })

    render(<Search onResultSelect={() => {}} />)
    const input = screen.getByPlaceholderText(/search/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('Test Result')).toBeDefined()
    })
  })

  it('calls onResultSelect when result is clicked', async () => {
    const onResultSelect = vi.fn()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        results: [
          { id: '1', title: 'Clickable Result', snippet: 'Click me', type: 'message' }
        ]
      })
    })

    render(<Search onResultSelect={onResultSelect} />)
    const input = screen.getByPlaceholderText(/search/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('Clickable Result')).toBeDefined()
    })

    await userEvent.click(screen.getByText('Clickable Result'))
    expect(onResultSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: '1', title: 'Clickable Result' })
    )
  })

  it('clears search when clear button is clicked', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ results: [] })
    })

    render(<Search onResultSelect={() => {}} />)
    const input = screen.getByPlaceholderText(/search/i)
    await userEvent.type(input, 'test query')

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /clear/i })).toBeDefined()
    })

    await userEvent.click(screen.getByRole('button', { name: /clear/i }))
    expect(input).toHaveValue('')
  })

  it('handles keyboard navigation', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        results: [
          { id: '1', title: 'Result 1', snippet: 'First', type: 'conversation' },
          { id: '2', title: 'Result 2', snippet: 'Second', type: 'message' }
        ]
      })
    })

    render(<Search onResultSelect={() => {}} />)
    const input = screen.getByPlaceholderText(/search/i)
    await userEvent.type(input, 'test')

    await waitFor(() => {
      expect(screen.getByText('Result 1')).toBeDefined()
    })

    await userEvent.keyboard('{ArrowDown}')
    await userEvent.keyboard('{Enter}')

    expect(screen.queryByText('Result 1')).toBeNull()
  })
})
