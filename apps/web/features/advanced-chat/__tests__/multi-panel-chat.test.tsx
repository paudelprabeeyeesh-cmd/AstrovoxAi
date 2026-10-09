import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { MultiPanelChat } from '../multi-panel-chat'

const mockModels = [
  { id: 'model-a', name: 'Model A', provider: 'Test' },
  { id: 'model-b', name: 'Model B', provider: 'Test' },
]

describe('MultiPanelChat', () => {
  it('renders panels for selected models', () => {
    const onSend = jest.fn()
    render(
      <MultiPanelChat models={mockModels} selectedModels={['model-a']} onSend={onSend} />
    )
    expect(screen.getByText('Model A')).toBeDefined()
  })

  it('sends message on submit', () => {
    const onSend = jest.fn()
    render(
      <MultiPanelChat models={mockModels} selectedModels={['model-a']} onSend={onSend} />
    )
    const textarea = screen.getByPlaceholderText(/send a message/i)
    fireEvent.change(textarea, { target: { value: 'Hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(onSend).toHaveBeenCalledWith('Hello', 'model-a')
  })

  it('shows empty state when no messages', () => {
    const onSend = jest.fn()
    render(
      <MultiPanelChat models={mockModels} selectedModels={['model-a']} onSend={onSend} />
    )
    expect(screen.getByText(/responses will appear here/i)).toBeDefined()
  })
})
