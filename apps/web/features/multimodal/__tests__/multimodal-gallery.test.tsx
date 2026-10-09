import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { MultimodalGallery } from '../multimodal-gallery'

const mockItems = [
  {
    id: '1',
    type: 'image' as const,
    url: 'https://example.com/img1.jpg',
    title: 'Photo 1',
    modality: 'vision',
    timestamp: new Date('2025-01-01'),
    tags: ['nature'],
  },
  {
    id: '2',
    type: 'audio' as const,
    url: 'https://example.com/audio1.mp3',
    title: 'Audio Clip',
    modality: 'speech',
    timestamp: new Date('2025-01-02'),
    tags: ['podcast'],
  },
  {
    id: '3',
    type: 'video' as const,
    url: 'https://example.com/vid1.mp4',
    title: 'Video 1',
    modality: 'vision',
    timestamp: new Date('2025-01-03'),
    tags: ['tutorial'],
  },
]

describe('MultimodalGallery', () => {
  it('renders empty state when no items', () => {
    render(<MultimodalGallery items={[]} />)
    expect(screen.getByText(/no media found/i)).toBeDefined()
  })

  it('renders media items', () => {
    render(<MultimodalGallery items={mockItems} />)
    expect(screen.getByText('Photo 1')).toBeDefined()
    expect(screen.getByText('Audio Clip')).toBeDefined()
    expect(screen.getByText('Video 1')).toBeDefined()
  })

  it('filters items by search query', () => {
    render(<MultimodalGallery items={mockItems} />)
    const input = screen.getByPlaceholderText(/search media/i)
    fireEvent.change(input, { target: { value: 'Audio' } })
    expect(screen.getByText('Audio Clip')).toBeDefined()
    expect(screen.queryByText('Photo 1')).toBeNull()
  })

  it('filters by modality', () => {
    render(<MultimodalGallery items={mockItems} />)
    const select = screen.getByDisplayValue('All Modalities')
    fireEvent.change(select, { target: { value: 'image' } })
    expect(screen.getByText('Photo 1')).toBeDefined()
    expect(screen.queryByText('Audio Clip')).toBeNull()
  })

  it('switches between grid and list view', () => {
    render(<MultimodalGallery items={mockItems} />)
    const listBtn = screen.getByTitle('List view')
    fireEvent.click(listBtn)
    const gridBtn = screen.getByTitle('Grid view')
    fireEvent.click(gridBtn)
    expect(screen.getByText('Photo 1')).toBeDefined()
  })

  it('calls onSelect when item is clicked', () => {
    const onSelect = jest.fn()
    render(<MultimodalGallery items={mockItems} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('Photo 1'))
    expect(onSelect).toHaveBeenCalledWith(mockItems[0])
  })

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = jest.fn()
    render(<MultimodalGallery items={mockItems} onDelete={onDelete} />)
    const deleteButtons = screen.getAllByTitle('Delete')
    fireEvent.click(deleteButtons[0])
    expect(onDelete).toHaveBeenCalledWith('1')
  })

  it('opens detail modal on item click', () => {
    render(<MultimodalGallery items={mockItems} />)
    fireEvent.click(screen.getByText('Photo 1'))
    expect(screen.getByText('vision')).toBeDefined()
  })

  it('shows tags in detail modal', () => {
    render(<MultimodalGallery items={mockItems} />)
    fireEvent.click(screen.getByText('Photo 1'))
    expect(screen.getByText('nature')).toBeDefined()
  })
})
