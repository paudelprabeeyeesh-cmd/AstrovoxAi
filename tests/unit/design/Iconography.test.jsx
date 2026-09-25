import { describe, it, expect } from 'vitest'
import Icon, { ICONS } from '../../src/design/Iconography'

describe('Iconography', () => {
  it('ICONS has expected icon names', () => {
    expect(ICONS).toHaveProperty('chat')
    expect(ICONS).toHaveProperty('send')
    expect(ICONS).toHaveProperty('settings')
    expect(ICONS).toHaveProperty('search')
    expect(ICONS).toHaveProperty('user')
  })

  it('Icon renders component for valid name', () => {
    const { container } = render(<Icon name="chat" />)
    expect(container.querySelector('svg')).not.toBeNull()
  })

  it('Icon returns null for unknown name', () => {
    const { container } = render(<Icon name="unknown-icon" />)
    expect(container.firstChild).toBeNull()
  })

  it('Icon applies custom className', () => {
    const { container } = render(<Icon name="send" className="my-icon" />)
    expect(container.querySelector('.my-icon')).not.toBeNull()
  })

  it('Icon applies custom size', () => {
    const { container } = render(<Icon name="send" size={32} />)
    const span = container.querySelector('span')
    expect(span?.style.width).toBe('32px')
    expect(span?.style.height).toBe('32px')
  })
})