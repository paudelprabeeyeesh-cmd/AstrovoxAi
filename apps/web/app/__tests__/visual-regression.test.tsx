
import React from 'react'
import { render, screen } from '@testing-library/react'

describe('Visual Regression Smoke Tests', () => {
  it('homepage renders expected heading', async () => {
    const mod = await import('@/app/page')
    const Page = mod.default
    render(<Page />)
    expect(screen.queryByRole('heading', { level: 1 })).toBeTruthy()
  })
})
