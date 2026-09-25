import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AnimatedContainer, AnimatedList, MOTION_PRESETS } from '../src/design/MotionLibrary'

describe('MotionLibrary - Advanced', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('applies fadeIn preset', () => {
    render(<AnimatedContainer preset="fadeIn"><div>Fading</div></AnimatedContainer>)
    expect(screen.getByText('Fading')).toBeDefined()
  })

  it('applies scaleIn preset', () => {
    render(<AnimatedContainer preset="scaleIn"><div>Scaling</div></AnimatedContainer>)
    expect(screen.getByText('Scaling')).toBeDefined()
  })

  it('applies bounceIn preset', () => {
    render(<AnimatedContainer preset="bounceIn"><div>Bouncing</div></AnimatedContainer>)
    expect(screen.getByText('Bouncing')).toBeDefined()
  })

  it('has stagger preset for lists', () => {
    render(
      <AnimatedList preset="stagger">
        <div>Item 1</div>
        <div>Item 2</div>
      </AnimatedList>
    )
    expect(screen.getByText('Item 1')).toBeDefined()
    expect(screen.getByText('Item 2')).toBeDefined()
  })

  it('has pulse preset', () => {
    expect(MOTION_PRESETS.pulse).toBeDefined()
    expect(MOTION_PRESETS.pulse.animate).toBeDefined()
  })

  it('has typing preset', () => {
    expect(MOTION_PRESETS.typing).toBeDefined()
    expect(MOTION_PRESETS.typing.initial).toBeDefined()
  })
})
