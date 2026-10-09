
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
}))

describe('End-to-End Critical Flows', () => {
  it('renders landing page without crashing', async () => {
    const mod = await import('@/app/page')
    const Page = mod.default
    const { container } = render(<Page />)
    expect(container.innerHTML).not.toBe('')
  })

  it('chat page renders input', async () => {
    const mod = await import('@/app/(app)/chat/page')
    const Page = mod.default
    render(<Page />)
    expect(screen.queryByPlaceholderText(/message/i)).toBeTruthy()
  })
})
