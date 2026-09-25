import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FeatureFlagsDashboard from '../src/components/dashboards/FeatureFlagsDashboard'

describe('FeatureFlagsDashboard', () => {
  const mockFlags = [
    { id: '1', name: 'New Chat UI', description: 'New chat interface', enabled: true, environment: 'production', rollout: 50 },
    { id: '2', name: 'Voice Input', description: 'Voice input feature', enabled: false, environment: 'staging', rollout: 0 },
    { id: '3', name: 'Beta Features', description: 'Beta features', enabled: true, environment: 'production', rollout: 10 }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders feature flags', () => {
    render(<FeatureFlagsDashboard flags={mockFlags} />)
    expect(screen.getByText('New Chat UI')).toBeDefined()
    expect(screen.getByText('Voice Input')).toBeDefined()
    expect(screen.getByText('Beta Features')).toBeDefined()
  })

  it('filters by enabled status', () => {
    render(<FeatureFlagsDashboard flags={mockFlags} />)
    fireEvent.click(screen.getByRole('button', { name: /disabled/i }))
    expect(screen.getByText('Voice Input')).toBeDefined()
    expect(screen.queryByText('New Chat UI')).toBeNull()
  })

  it('calls onToggle when toggle clicked', () => {
    const onToggle = vi.fn()
    render(<FeatureFlagsDashboard flags={mockFlags} onToggle={onToggle} />)
    const toggles = screen.getAllByRole('switch')
    fireEvent.click(toggles[0])
    expect(onToggle).toHaveBeenCalledWith('1', false)
  })
})
