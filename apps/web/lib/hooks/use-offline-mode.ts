'use client'

import { useEffect, useState, useCallback } from 'react'
import { toast } from '@/hooks/use-toast'

interface OfflineState {
  isOnline: boolean
  wasOffline: boolean
  pendingActions: Array<{
    id: string
    type: string
    data: unknown
    timestamp: number
  }>
}

export function useOfflineMode() {
  const [state, setState] = useState<OfflineState>({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    wasOffline: false,
    pendingActions: [],
  })

  const goOnline = useCallback(() => {
    setState((prev) => {
      const wasOffline = !prev.isOnline
      return {
        ...prev,
        isOnline: true,
        wasOffline,
      }
    })

    if (state.wasOffline) {
      toast({
        title: 'Back Online',
        description: 'Your connection has been restored.',
      })
    }
  }, [state.wasOffline, toast])

  const goOffline = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isOnline: false,
      wasOffline: true,
    }))

    toast({
      title: 'You are offline',
      description: 'Some features may be limited. Changes will sync when you reconnect.',
      variant: 'destructive',
    })
  }, [toast])

  const queueAction = useCallback((type: string, data: unknown) => {
    setState((prev) => ({
      ...prev,
      pendingActions: [
        ...prev.pendingActions,
        {
          id: crypto.randomUUID(),
          type,
          data,
          timestamp: Date.now(),
        },
      ],
    }))
  }, [])

  const syncPendingActions = useCallback(async () => {
    if (!state.isOnline || state.pendingActions.length === 0) return

    for (const action of state.pendingActions) {
      try {
        await fetch('/api/offline/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(action),
        })
      } catch (err) {
        console.error('Failed to sync action:', action, err)
      }
    }

    setState((prev) => ({
      ...prev,
      pendingActions: [],
    }))
  }, [state.isOnline, state.pendingActions])

  useEffect(() => {
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)

    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [goOnline, goOffline])

  useEffect(() => {
    if (state.isOnline && state.pendingActions.length > 0) {
      syncPendingActions()
    }
  }, [state.isOnline, state.pendingActions.length, syncPendingActions])

  return {
    isOnline: state.isOnline,
    wasOffline: state.wasOffline,
    pendingActions: state.pendingActions,
    queueAction,
    syncPendingActions,
  }
}

export function usePWA() {
  const [isPWA, setIsPWA] = useState(false)
  const [canInstall, setCanInstall] = useState(false)
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null)

  useEffect(() => {
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches
    const isIosStandalone = (window.navigator as any).standalone
    setIsPWA(isStandalone || isIosStandalone)

    const handler = (e: Event) => {
      e.preventDefault()
      setDeferredPrompt(e)
      setCanInstall(true)
    }

    window.addEventListener('beforeinstallprompt', handler)

    return () => {
      window.removeEventListener('beforeinstallprompt', handler)
    }
  }, [])

  const install = useCallback(async () => {
    if (!deferredPrompt) return false

    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice

    setDeferredPrompt(null)
    setCanInstall(false)

    return outcome === 'accepted'
  }, [deferredPrompt])

  return {
    isPWA,
    canInstall,
    install,
  }
}
