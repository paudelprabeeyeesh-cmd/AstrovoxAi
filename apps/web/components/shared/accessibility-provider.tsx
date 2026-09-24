'use client'

import { useEffect } from 'react'

export function AccessibilityProvider() {
  useEffect(() => {
    const style = document.createElement('style')
    style.id = 'a11y-focus-styles'
    style.textContent = `
      .focus-visible-ring:focus-visible {
        outline: 2px solid #3b82f6;
        outline-offset: 2px;
      }
      .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border-width: 0;
      }
    `
    document.head.appendChild(style)

    return () => {
      document.head.removeChild(style)
    }
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        const activeEl = document.activeElement
        if (activeEl && activeEl instanceof HTMLElement) {
          activeEl.blur()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    const liveRegions: Array<{ region: HTMLDivElement; timeout: NodeJS.Timeout }> = []

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach((node) => {
            if (node instanceof HTMLElement && node.dataset.liveRegion) {
              const timeout = setTimeout(() => {
                node.textContent = ''
              }, 1000)
              liveRegions.push({ region: node, timeout })
            }
          })
        }
      })
    })

    observer.observe(document.body, { childList: true, subtree: true })

    return () => {
      observer.disconnect()
      liveRegions.forEach(({ region, timeout }) => {
        clearTimeout(timeout)
        region.remove()
      })
    }
  }, [])

  return null
}

export function useAccessibility() {
  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    const region = document.createElement('div')
    region.setAttribute('role', 'status')
    region.setAttribute('aria-live', priority)
    region.setAttribute('aria-atomic', 'true')
    region.dataset.liveRegion = 'true'
    region.className = 'sr-only'
    document.body.appendChild(region)

    requestAnimationFrame(() => {
      region.textContent = message
    })

    setTimeout(() => {
      region.remove()
    }, 1000)
  }, [])

  return { announce }
}
