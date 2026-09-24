import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { VideoChat } from '../video-chat'

describe('VideoChat', () => {
  it('renders upload drop zone', () => {
    render(<VideoChat />)
    expect(screen.getByText(/drop a video here/i)).toBeDefined()
  })

  it('shows error for invalid file type', () => {
    render(<VideoChat />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.txt', { type: 'text/plain' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    expect(screen.getByText(/please select a valid video/i)).toBeDefined()
  })

  it('accepts valid video file by extension', () => {
    render(<VideoChat />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.mp4', { type: 'video/mp4' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    expect(screen.getByText('Analyze Video')).toBeDefined()
  })

  it('calls onAnalyze when analyze button is clicked', async () => {
    const onAnalyze = jest.fn()
    render(<VideoChat onAnalyze={onAnalyze} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.mp4', { type: 'video/mp4' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    const analyzeBtn = screen.getByText('Analyze Video')
    fireEvent.click(analyzeBtn)
  })

  it('shows remove button after video is loaded', () => {
    render(<VideoChat />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.mp4', { type: 'video/mp4' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    expect(screen.getByText('Remove')).toBeDefined()
  })

  it('disables controls when disabled prop is true', () => {
    render(<VideoChat disabled />)
    const dropZone = screen.getByText(/drop a video here/i).closest('div')
    expect(dropZone).toHaveClass('opacity-50')
  })
})
