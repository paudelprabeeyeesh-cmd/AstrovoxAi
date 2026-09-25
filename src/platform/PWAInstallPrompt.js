import { useState, useEffect, useCallback } from 'react'
import { createStorage } from '../utils/storage'
import { isMobile } from '../utils/platform'

const PWA_STORAGE = createStorage('pwa')

export function usePWAInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [isInstalled, setIsInstalled] = useState(false)
  const [isStandalone, setIsStandalone] = useState(false)
  const [showPrompt, setShowPrompt] = useState(false)

  useEffect(() => {
    setIsStandalone(
      window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true ||
      document.referrer.includes('android-app://')
    )

    const alreadyInstalled = PWA_STORAGE.get('installed')
    setIsInstalled(alreadyInstalled === true)

    const handleBeforeInstall = (e) => {
      e.preventDefault()
      setDeferredPrompt(e)
      if (!alreadyInstalled && !isStandalone) {
        setShowPrompt(true)
      }
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstall)

    window.addEventListener('appinstalled', () => {
      setDeferredPrompt(null)
      setIsInstalled(true)
      PWA_STORAGE.set('installed', true)
      setShowPrompt(false)
    })

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall)
    }
  }, [])

  const install = useCallback(async () => {
    if (!deferredPrompt) return { installed: false }

    try {
      deferredPrompt.prompt()
      const { outcome } = await deferredPrompt.userChoice
      if (outcome === 'accepted') {
        setIsInstalled(true)
        PWA_STORAGE.set('installed', true)
        setDeferredPrompt(null)
        setShowPrompt(false)
        return { installed: true, outcome }
      }
      return { installed: false, outcome }
    } catch (e) {
      console.error('PWA install failed:', e)
      return { installed: false, error: e.message }
    }
  }, [deferredPrompt])

  const dismiss = useCallback(() => {
    setShowPrompt(false)
    PWA_STORAGE.set('install_dismissed', true)
  }, [])

  const canInstall = useCallback(() => {
    return deferredPrompt !== null && !isInstalled && !isStandalone && !PWA_STORAGE.get('install_dismissed')
  }, [deferredPrompt, isInstalled, isStandalone])

  return {
    canInstall: canInstall(),
    isInstalled,
    isStandalone,
    showPrompt,
    install,
    dismiss
  }
}

export function PWAInstallPrompt({ onInstall, onDismiss }) {
  const { canInstall, showPrompt, install, dismiss } = usePWAInstall()

  useEffect(() => {
    if (!canInstall || !showPrompt) return
  }, [canInstall, showPrompt])

  if (!showPrompt || !canInstall) return null

  return (
    <div style={{
      position: 'fixed',
      bottom: 20,
      left: '50%',
      transform: 'translateX(-50%)',
      backgroundColor: 'rgba(4, 8, 20, 0.95)',
      border: '1px solid #1e293b',
      borderRadius: 16,
      padding: 20,
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      maxWidth: 400,
      width: '90%',
      zIndex: 99999,
      boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      fontFamily: 'monospace'
    }}>
      <div style={{
        width: 48,
        height: 48,
        borderRadius: 12,
        background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 24,
        flexShrink: 0
      }}>
        🛸
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ color: '#67e8f9', fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
          Install Astrovox AI
        </div>
        <div style={{ color: '#94a3b8', fontSize: 12 }}>
          Add to home screen for a native app experience
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button
          onClick={dismiss}
          style={{
            padding: '8px 12px',
            background: 'transparent',
            border: '1px solid #1e293b',
            color: '#94a3b8',
            borderRadius: 8,
            cursor: 'pointer',
            fontSize: 12
          }}
        >
          Later
        </button>
        <button
          onClick={async () => {
            const result = await install()
            onInstall?.(result)
          }}
          style={{
            padding: '8px 16px',
            background: '#06b6d4',
            border: 'none',
            color: '#02040a',
            borderRadius: 8,
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: 12
          }}
        >
          Install
        </button>
      </div>
    </div>
  )
}
