import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import FolderSystem from '../../src/components/workspace/FolderSystem'

describe('FolderSystem', () => {
  const mockFolders = [
    { id: '1', name: 'Work' },
    { id: '2', name: 'Personal' },
    { id: '3', name: 'Projects' }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders folder list', () => {
    render(<FolderSystem folders={mockFolders} activeFolder={null} onSelectFolder={() => {}} />)
    expect(screen.getByText('Work')).toBeDefined()
    expect(screen.getByText('Personal')).toBeDefined()
    expect(screen.getByText('Projects')).toBeDefined()
  })

  it('highlights active folder', () => {
    render(<FolderSystem folders={mockFolders} activeFolder="2" onSelectFolder={() => {}} />)
    expect(screen.getByText('Personal')).toBeDefined()
  })

  it('calls onSelectFolder when folder clicked', () => {
    const onSelectFolder = vi.fn()
    render(<FolderSystem folders={mockFolders} activeFolder={null} onSelectFolder={onSelectFolder} />)
    fireEvent.click(screen.getByText('Work'))
    expect(onSelectFolder).toHaveBeenCalledWith('1')
  })

  it('shows new folder button', () => {
    render(<FolderSystem folders={mockFolders} activeFolder={null} onSelectFolder={() => {}} onCreateFolder={() => {}} />)
    expect(screen.getByRole('button', { name: /new/i })).toBeDefined()
  })
})
