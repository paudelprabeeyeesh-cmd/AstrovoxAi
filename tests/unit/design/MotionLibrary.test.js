import { describe, it, expect } from 'vitest'
import { MOTION_PRESETS } from '../../src/design/MotionLibrary'

describe('MotionLibrary', () => {
  it('MOTION_PRESETS has expected presets', () => {
    expect(MOTION_PRESETS).toHaveProperty('fadeIn')
    expect(MOTION_PRESETS).toHaveProperty('slideUp')
    expect(MOTION_PRESETS).toHaveProperty('slideIn')
    expect(MOTION_PRESETS).toHaveProperty('scaleIn')
    expect(MOTION_PRESETS).toHaveProperty('bounceIn')
    expect(MOTION_PRESETS).toHaveProperty('stagger')
    expect(MOTION_PRESETS).toHaveProperty('pulse')
    expect(MOTION_PRESETS).toHaveProperty('typing')
  })

  it('fadeIn preset has initial, animate, exit, and transition', () => {
    const preset = MOTION_PRESETS.fadeIn
    expect(preset).toHaveProperty('initial')
    expect(preset).toHaveProperty('animate')
    expect(preset).toHaveProperty('exit')
    expect(preset).toHaveProperty('transition')
  })

  it('slideUp preset has y values', () => {
    const preset = MOTION_PRESETS.slideUp
    expect(preset.initial.y).toBeGreaterThan(0)
    expect(preset.animate.y).toBe(0)
  })

  it('bounceIn preset uses spring transition', () => {
    const preset = MOTION_PRESETS.bounceIn
    expect(preset.transition.type).toBe('spring')
    expect(preset.transition.stiffness).toBeGreaterThan(0)
  })

  it('stagger preset has staggerChildren', () => {
    const preset = MOTION_PRESETS.stagger
    expect(preset.transition.staggerChildren).toBeGreaterThan(0)
  })

  it('pulse preset has repeat Infinity', () => {
    const preset = MOTION_PRESETS.pulse
    expect(preset.transition.repeat).toBe(Infinity)
  })
})