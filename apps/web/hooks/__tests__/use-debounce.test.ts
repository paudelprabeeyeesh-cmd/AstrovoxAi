import React from 'react'
import { renderHook, act } from '@testing-library/react'
import { useDebounce } from '@/hooks/use-debounce'

describe('useDebounce', () => {
  beforeEach(() => {
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('delays callback execution', () => {
    const callback = jest.fn()
    const debounced = useDebounce(callback, 500)

    act(() => {
      debounced()
    })

    expect(callback).not.toHaveBeenCalled()

    act(() => {
      jest.advanceTimersByTime(500)
    })

    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('cancels previous timeout on repeated calls', () => {
    const callback = jest.fn()
    const debounced = useDebounce(callback, 500)

    act(() => {
      debounced()
    })

    act(() => {
      jest.advanceTimersByTime(300)
      debounced()
    })

    act(() => {
      jest.advanceTimersByTime(500)
    })

    expect(callback).toHaveBeenCalledTimes(1)
  })
})
