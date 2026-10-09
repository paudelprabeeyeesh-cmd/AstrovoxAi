'use client'

import { useEffect } from 'react'
import { useOfflineMode, usePWA } from '@/lib/hooks/use-offline-mode'

export function PWAProvider() {
  const { isOnline } = useOfflineMode()
  const { isPWA } = usePWA()

  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          console.log('SW registered:', registration.scope)
        })
        .catch((error) => {
          console.error('SW registration failed:', error)
        })
    }
  }, [])

  useEffect(() => {
    if (!isPWA) {
      const metaThemeColor = document.querySelector('meta[name="theme-color"]')
      if (metaThemeColor) {
        metaThemeColor.setAttribute('content', isOnline ? '#000000' : '#7f1d1d')
      }
    }
  }, [isOnline, isPWA])

  return null
}
