import { useState, useEffect, useCallback } from 'react'
import { createStorage } from '../utils/storage'
import { isMobile } from '../utils/platform'

const PWA_STORAGE = createStorage('pwa')
const UPDATE_STORAGE = createStorage('pwa_update')

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

    const handleAppInstalled = () => {
      setDeferredPrompt(null)
      setIsInstalled(true)
      PWA_STORAGE.set('installed', true)
      setShowPrompt(false)
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstall)
    window.addEventListener('appinstalled', handleAppInstalled)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall)
      window.removeEventListener('appinstalled', handleAppInstalled)
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

export function usePWAUpdate() {
  const [updateAvailable, setUpdateAvailable] = useState(false)
  const [newVersion, setNewVersion] = useState(null)
  const [isUpdating, setIsUpdating] = useState(false)

  useEffect(() => {
    async function checkForUpdates() {
      try {
        const currentVersion = PWA_STORAGE.get('version') || '1.0.0'

        const response = await fetch('/api/pwa/version', {
          method: 'GET',
          headers: { 'Cache-Control': 'no-cache' }
        }).catch(() => null)

        if (response?.ok) {
          const { version, minSupportedVersion, changelog } = await response.json()

          if (isVersionNewer(version, currentVersion)) {
            setNewVersion({
              version,
              minSupportedVersion,
              changelog
            })
            setUpdateAvailable(true)
          }
        }

        if ('serviceWorker' in navigator) {
          const registration = await navigator.serviceWorker.getRegistration()
          if (registration) {
            registration.addEventListener('updatefound', () => {
              const newWorker = registration.installing
              if (newWorker) {
                newWorker.addEventListener('statechange', () => {
                  if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                    setUpdateAvailable(true)
                    UPDATE_STORAGE.set('pending_update', {
                      version,
                      timestamp: new Date().toISOString()
                    })
                  }
                })
              }
            })

            window.addEventListener('sw.update', (event) => {
              setNewVersion(event.detail)
              setUpdateAvailable(true)
            })
          }
        }
      } catch (e) {
        console.error('Update check failed:', e)
      }
    }

    checkForUpdates()

    const interval = setInterval(checkForUpdates, 60000)
    return () => clearInterval(interval)
  }, [])

  const applyUpdate = useCallback(async () => {
    if (!('serviceWorker' in navigator)) return false

    try {
      setIsUpdating(true)
      const registration = await navigator.serviceWorker.getRegistration()
      if (registration?.waiting) {
        registration.waiting.postMessage({ type: 'SKIP_WAITING' })
      }

      window.addEventListener('controllerchange', () => {
        window.location.reload()
      }, { once: true })

      return true
    } catch (e) {
      console.error('Update apply failed:', e)
      return false
    } finally {
      setIsUpdating(false)
    }
  }, [])

  const dismissUpdate = useCallback(() => {
    setUpdateAvailable(false)
    setNewVersion(null)
    UPDATE_STORAGE.set('update_dismissed', true)
  }, [])

  return {
    updateAvailable,
    newVersion,
    isUpdating,
    applyUpdate,
    dismissUpdate
  }
}

export function PWAInstallPrompt({ onInstall, onDismiss, onUpdate }) {
  const { canInstall, showPrompt, install, dismiss } = usePWAInstall()
  const { updateAvailable, newVersion, applyUpdate, dismissUpdate } = usePWAUpdate()

  if (!showPrompt || !canInstall) {
    if (!updateAvailable) return null
  }

  if (updateAvailable && newVersion) {
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
          🚀
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ color: '#67e8f9', fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
            Update Available
          </div>
          <div style={{ color: '#94a3b8', fontSize: 12 }}>
            Version {newVersion.version} is ready
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          <button
            onClick={dismissUpdate}
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
              const result = await applyUpdate()
              onUpdate?.(result)
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
            Update
          </button>
        </div>
      </div>
    )
  }

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

function isVersionNewer(newVersion, currentVersion) {
  if (!newVersion || !currentVersion) return false
  if (newVersion === currentVersion) return false

  const normalize = (v) => v.split('.').map(n => parseInt(n) || 0)
  const newParts = normalize(newVersion)
  const currentParts = normalize(currentVersion)

  for (let i = 0; i < Math.max(newParts.length, currentParts.length); i++) {
    const newPart = newParts[i] || 0
    const currentPart = currentParts[i] || 0
    if (newPart > currentPart) return true
    if (newPart < currentPart) return false
  }
  return false
}
