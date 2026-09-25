import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PerformanceDashboard from '../src/components/dashboards/PerformanceDashboard'

describe('PerformanceDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders performance profiler', () => {
    render(<PerformanceDashboard />)
    expect(screen.getByText('Performance Profiler')).toBeDefined()
  })

  it('displays time range selector', () => {
    render(<PerformanceDashboard />)
    expect(screen.getByRole('combobox', { name: /last 1 hour/i })).toBeDefined()
  })

  it('shows live toggle button', () => {
    render(<PerformanceDashboard />)
    expect(screen.getByRole('button', { name: /live/i })).toBeDefined()
  })

  it('displays metric cards', () => {
    render(<PerformanceDashboard />)
    expect(screen.getByText('Current')).toBeDefined()
    expect(screen.getByText('P99')).toBeDefined()
    expect(screen.getByText('Avg')).toBeDefined()
    expect(screen.getByText('Range')).toBeDefined()
  })

  it('renders sparkline chart', () => {
    render(<PerformanceDashboard />)
    const svg = document.querySelector('svg')
    expect(svg).toBeDefined()
  })

  it('toggles live mode', async () => {
    render(<PerformanceDashboard />)
    const liveButton = screen.getByRole('button', { name: /live/i })
    await userEvent.click(liveButton)
    expect(screen.getByRole('button', { name: /paused/i })).toBeDefined()
  })

  it('changes time range', async () => {
    render(<PerformanceDashboard />)
    const select = screen.getAllByRole('combobox')[0]
    await userEvent.selectOptions(select, '24h')
    expect(select).toHaveValue('24h')
  })
})
