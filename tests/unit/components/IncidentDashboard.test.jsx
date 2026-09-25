import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import IncidentDashboard from '../src/components/dashboards/IncidentDashboard'

describe('IncidentDashboard', () => {
  const mockIncidents = [
    { id: '1', title: 'API Latency', service: 'chat-api', severity: 'high', status: 'active', timestamp: Date.now() },
    { id: '2', title: 'Database Error', service: 'postgres', severity: 'critical', status: 'investigating', timestamp: Date.now() - 3600000 },
    { id: '3', title: 'UI Glitch', service: 'frontend', severity: 'low', status: 'resolved', timestamp: Date.now() - 7200000 }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders incident dashboard', () => {
    render(<IncidentDashboard incidents={mockIncidents} />)
    expect(screen.getByText('Incident Dashboard')).toBeDefined()
  })

  it('shows active incident count', () => {
    render(<IncidentDashboard incidents={mockIncidents} />)
    expect(screen.getByText('2 Active')).toBeDefined()
  })

  it('filters incidents by severity', () => {
    render(<IncidentDashboard incidents={mockIncidents} />)
    fireEvent.click(screen.getByRole('button', { name: /active/i }))
    expect(screen.getByText('API Latency')).toBeDefined()
    expect(screen.getByText('Database Error')).toBeDefined()
  })

  it('shows incident details', () => {
    render(<IncidentDashboard incidents={mockIncidents} />)
    expect(screen.getByText('API Latency')).toBeDefined()
    expect(screen.getByText('chat-api')).toBeDefined()
  })
})
