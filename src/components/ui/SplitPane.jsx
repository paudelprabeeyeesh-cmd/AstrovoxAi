import React, { useState, useRef, useCallback, useEffect } from 'react'
import { useA11y } from './A11yProvider'

export function SplitPane({
  direction = 'horizontal',
  minSize = 200,
  maxSize = 800,
  defaultLeftSize = 50,
  left,
  right,
  onResize
}) {
  const [leftSize, setLeftSize] = useState(defaultLeftSize)
  const [isDragging, setIsDragging] = useState(false)
  const containerRef = useRef(null)
  const startPosRef = useRef(0)
  const startSizeRef = useRef(0)
  const { announce } = useA11y()

  const handleMouseDown = useCallback((e) => {
    e.preventDefault()
    setIsDragging(true)
    startPosRef.current = direction === 'horizontal' ? e.clientX : e.clientY
    startSizeRef.current = leftSize
  }, [direction, leftSize])

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e) => {
      if (!containerRef.current) return
      const containerRect = containerRef.current.getBoundingClientRect()
      const currentPos = direction === 'horizontal' ? e.clientX : e.clientY
      const containerSize = direction === 'horizontal' ? containerRect.width : containerRect.height
      const delta = currentPos - startPosRef.current
      const newSize = Math.max(minSize, Math.min(maxSize, startSizeRef.current + delta))
      const percentage = Math.round((newSize / containerSize) * 100)
      setLeftSize(percentage)
      onResize?.(percentage)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      announce(`Pane resized to ${Math.round(leftSize)} percent`)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, direction, minSize, maxSize, leftSize, announce, onResize])

  const handleKeyDown = useCallback((e) => {
    const step = e.shiftKey ? 10 : 1
    let newSize = leftSize

    if (direction === 'horizontal') {
      if (e.key === 'ArrowLeft') {
        newSize = Math.max(minSize, leftSize - step)
      } else if (e.key === 'ArrowRight') {
        newSize = Math.min(maxSize, leftSize + step)
      } else {
        return
      }
    } else {
      if (e.key === 'ArrowUp') {
        newSize = Math.max(minSize, leftSize - step)
      } else if (e.key === 'ArrowDown') {
        newSize = Math.min(maxSize, leftSize + step)
      } else {
        return
      }
    }

    e.preventDefault()
    setLeftSize(newSize)
    onResize?.(newSize)
    announce(`Pane resized to ${newSize} percent`)
  }, [direction, leftSize, minSize, maxSize, announce, onResize])

  const isHorizontal = direction === 'horizontal'
  const cursor = isDragging ? 'grabbing' : 'grab'

  return (
    <div
      ref={containerRef}
      style={{
        display: 'flex',
        flexDirection: isHorizontal ? 'row' : 'column',
        width: '100%',
        height: '100%',
        position: 'relative'
      }}
      role="separator"
      aria-orientation={direction}
      aria-valuenow={Math.round(leftSize)}
      aria-valuemin={minSize}
      aria-valuemax={maxSize}
      aria-label={`Resizable ${direction} split pane`}
    >
      <div style={{
        width: isHorizontal ? `${leftSize}%` : '100%',
        height: isHorizontal ? '100%' : `${leftSize}%`,
        overflow: 'hidden',
        minWidth: isHorizontal ? `${minSize}px` : undefined,
        minHeight: isHorizontal ? undefined : `${minSize}px`
      }}>
        {left}
      </div>
      <div
        role="separator"
        tabIndex={0}
        onMouseDown={handleMouseDown}
        onKeyDown={handleKeyDown}
        style={{
          width: isHorizontal ? '6px' : '100%',
          height: isHorizontal ? '100%' : '6px',
          cursor: cursor,
          backgroundColor: isDragging ? 'var(--astrovox-primary)' : 'transparent',
          border: isDragging ? 'none' : '1px solid transparent',
          transition: isDragging ? 'none' : 'background-color 0.2s, border-color 0.2s',
          position: 'relative',
          zIndex: 10,
          flexShrink: 0,
          outline: 'none'
        }}
        onMouseEnter={(e) => {
          if (!isDragging) {
            e.currentTarget.style.borderColor = 'var(--astrovox-border)'
            e.currentTarget.style.backgroundColor = 'var(--astrovox-surface-hover)'
          }
        }}
        onMouseLeave={(e) => {
          if (!isDragging) {
            e.currentTarget.style.borderColor = 'transparent'
            e.currentTarget.style.backgroundColor = 'transparent'
          }
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = 'var(--astrovox-border-focus)'
          e.currentTarget.style.boxShadow = '0 0 0 2px var(--astrovox-border-focus)'
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = 'transparent'
          e.currentTarget.style.boxShadow = 'none'
        }}
        aria-label={`${direction} resize handle. Use arrow keys to resize.`}
      />
      <div style={{
        width: isHorizontal ? `${100 - leftSize}%` : '100%',
        height: isHorizontal ? '100%' : `${100 - leftSize}%`,
        overflow: 'hidden',
        minWidth: isHorizontal ? `${minSize}px` : undefined,
        minHeight: isHorizontal ? undefined : `${minSize}px`
      }}>
        {right}
      </div>
    </div>
  )
}
