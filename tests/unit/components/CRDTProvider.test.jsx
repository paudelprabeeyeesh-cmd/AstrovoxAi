import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CRDTProvider, useCRDT } from '../../src/components/crdt/CRDTProvider'

function TestConsumer({ onValue }) {
  const ctx = useCRDT()
  if (onValue) onValue(ctx)
  return <div data-testid="crdt-consumer">Ready</div>
}

describe('CRDTProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('provides CRDT context', () => {
    let captured
    render(
      <CRDTProvider documentId="doc-1" userId="user-1">
        <TestConsumer onValue={(v) => { captured = v }} />
      </CRDTProvider>
    )
    expect(captured.documentId).toBe('doc-1')
    expect(captured.userId).toBe('user-1')
  })

  it('exposes insert, delete, update operations', () => {
    let captured
    render(
      <CRDTProvider documentId="doc-1" userId="user-1">
        <TestConsumer onValue={(v) => { captured = v }} />
      </CRDTProvider>
    )
    expect(typeof captured.insert).toBe('function')
    expect(typeof captured.delete).toBe('function')
    expect(typeof captured.update).toBe('function')
  })

  it('tracks peer list', () => {
    let captured
    render(
      <CRDTProvider documentId="doc-1" userId="user-1">
        <TestConsumer onValue={(v) => { captured = v }} />
      </CRDTProvider>
    )
    expect(Array.isArray(captured.peers)).toBe(true)
  })

  it('throws when used outside provider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => render(<TestConsumer />)).toThrow('useCRDT must be used within CRDTProvider')
    consoleError.mockRestore()
  })

  it('exposes connect method', () => {
    let captured
    render(
      <CRDTProvider documentId="doc-1" userId="user-1">
        <TestConsumer onValue={(v) => { captured = v }} />
      </CRDTProvider>
    )
    expect(typeof captured.connect).toBe('function')
  })
})
