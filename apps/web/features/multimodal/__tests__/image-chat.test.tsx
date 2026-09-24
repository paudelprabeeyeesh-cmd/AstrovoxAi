import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { ImageChat } from '../image-chat'

describe('ImageChat', () => {
  it('renders drop zone', () => {
    render(<ImageChat />)
    expect(screen.getByText(/drop an image here/i)).toBeDefined()
  })

  it('calls onImageAnalyze with url on upload', async () => {
    const onImageAnalyze = jest.fn()
    render(<ImageChat onImageAnalyze={onImageAnalyze} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.png', { type: 'image/png' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    expect(onImageAnalyze).toHaveBeenCalledTimes(1)
    expect(typeof onImageAnalyze.mock.calls[0][0]).toBe('string')
  })

  it('shows error for non-image files', () => {
    render(<ImageChat />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.txt', { type: 'text/plain' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    expect(screen.getByText(/please select a valid image/i)).toBeDefined()
  })

  it('shows upload spinner while loading', () => {
    render(<ImageChat />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.png', { type: 'image/png' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    expect(screen.getByText(/image attached/i)).toBeDefined()
  })

  it('calls onTextWithImage when provided', async () => {
    const onTextWithImage = jest.fn()
    render(<ImageChat onTextWithImage={onTextWithImage} />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File([''], 'test.png', { type: 'image/png' })
    const dt = new DataTransfer()
    dt.items.add(file)
    fireEvent.change(input, { target: { files: dt.files } })
    expect(onTextWithImage).not.toHaveBeenCalled()
  })

  it('disables interaction when disabled prop is true', () => {
    render(<ImageChat disabled />)
    const dropZone = screen.getByText(/drop an image here/i).closest('div')
    expect(dropZone).toHaveClass('opacity-50')
  })
})
