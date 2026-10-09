import React from 'react'
import { render, screen } from '@testing-library/react'
import { ConfidenceMeter } from '../confidence-meter'

describe('ConfidenceMeter', () => {
  it('renders high confidence with green', () => {
    render(<ConfidenceMeter value={0.9} label="Model Confidence" />)
    expect(screen.getByText('Model Confidence')).toBeDefined()
    expect(screen.getByText('90.0%')).toBeDefined()
  })

  it('renders low confidence with red', () => {
    render(<ConfidenceMeter value={0.2} />)
    expect(screen.getByText('20.0%')).toBeDefined()
  })

  it('shows caution tooltip for medium confidence', () => {
    render(<ConfidenceMeter value={0.5} />)
    expect(screen.getByText('50.0%')).toBeDefined()
  })

  it('hides label when showLabel is false', () => {
    render(<ConfidenceMeter value={0.8} showLabel={false} />)
    expect(screen.queryByText('Confidence')).toBeNull()
  })
})
