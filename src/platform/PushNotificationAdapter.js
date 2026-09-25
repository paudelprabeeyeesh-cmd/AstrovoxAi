import { useState, useEffect, useCallback } from 'react'
import { createStorage } from '../utils/storage'
import { supportsPush, isOnline } from '../utils/platform'

const PUSH_STORAGE = createStorage('push')
const PUSH_PERMISSION_KEY = 'astrovox-push-permission'
const PUSH_SUBSCRIPTION_KEY = 'astrovox-push-subscription'

export function usePushNotifications() {
  const [permission, setPermission] = useState('default')
  const [subscription, setSubscription] = useState(null)
  const [supported, setSupported] = useState(false)

  useEffect(() => {
    setSupported(supportsPush())
    if (typeof Notification !== 'undefined') {
      setPermission(Notification.permission)
    }
    loadSubscription()
  }, [])

  const loadSubscription = useCallback(() => {
    try {
      const saved = PUSH_STORAGE.get(PUSH_SUBSCRIPTION_KEY)
      if (saved) {
        setSubscription(saved)
      }
    } catch (e) {
      console.error('Failed to load push subscription:', e)
    }
  }, [])

  const requestPermission = useCallback(async () => {
    if (!supported) {
      return { granted: false, reason: 'Push notifications not supported' }
    }

    try {
      const result = await Notification.requestPermission()
      setPermission(result)

      if (result === 'granted') {
        PUSH_STORAGE.set(PUSH_PERMISSION_KEY, 'granted')
        const sub = await subscribeToPush()
        if (sub) {
          setSubscription(sub)
          PUSH_STORAGE.set(PUSH_SUBSCRIPTION_KEY, sub)
        }
        return { granted: true, subscription: sub }
      } else {
        PUSH_STORAGE.set(PUSH_PERMISSION_KEY, 'denied')
        return { granted: false, reason: 'Permission denied' }
      }
    } catch (e) {
      return { granted: false, reason: e.message }
    }
  }, [supported])

  const subscribeToPush = useCallback(async () => {
    try {
      if (!('serviceWorker' in navigator)) return null

      const registration = await navigator.serviceWorker.ready
      const sub = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(import.meta.env.VITE_VAPID_PUBLIC_KEY || '')
      })
      return sub.toJSON()
    } catch (e) {
      console.error('Push subscription failed:', e)
      return null
    }
  }, [])

  const unsubscribe = useCallback(async () => {
    try {
      if (!('serviceWorker' in navigator)) return false

      const registration = await navigator.serviceWorker.ready
      const sub = await registration.pushManager.getSubscription()
      if (sub) {
        await sub.unsubscribe()
        setSubscription(null)
        PUSH_STORAGE.remove(PUSH_SUBSCRIPTION_KEY)
        PUSH_STORAGE.set(PUSH_PERMISSION_KEY, 'default')
        setPermission('default')
        return true
      }
    } catch (e) {
      console.error('Push unsubscribe failed:', e)
    }
    return false
  }, [])

  const showLocalNotification = useCallback((title, options = {}) => {
    if (!supported || permission !== 'granted') return

    try {
      const notif = new Notification(title, {
        icon: '/favicon.ico',
        badge: '/badge-72x72.png',
        tag: options.tag || 'astrovox-notification',
        renotify: false,
        ...options
      })
      notif.onclick = () => {
        window.focus()
        notif.close()
      }
      return notif
    } catch (e) {
      console.error('Local notification failed:', e)
    }
  }, [supported, permission])

  return {
    supported,
    permission,
    subscription,
    requestPermission,
    unsubscribe,
    showLocalNotification
  }
}

export function PushNotificationAdapter() {
  const { supported, permission, requestPermission, unsubscribe, showLocalNotification } = usePushNotifications()

  useEffect(() => {
    if (!supported) return

    const handlePushMessage = (event) => {
      try {
        const data = event.data?.json() || {}
        showLocalNotification(data.title || 'Astrovox AI', {
          body: data.body || data.message || 'You have a new notification',
          data: data.payload || {}
        })
      } catch (e) {
        console.error('Push message handling failed:', e)
      }
    }

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', handlePushMessage)
    }
    navigator.addEventListener('push', handlePushMessage)

    return () => {
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.removeEventListener('message', handlePushMessage)
      }
      navigator.removeEventListener('push', handlePushMessage)
    }
  }, [supported, showLocalNotification])

  useEffect(() => {
    if (!supported) return
    if (permission === 'granted' && !PUSH_STORAGE.get(PUSH_PERMISSION_KEY)) {
      PUSH_STORAGE.set(PUSH_PERMISSION_KEY, 'granted')
    }
  }, [supported, permission])

  return null
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4)
  const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from(raw, c => c.charCodeAt(0))
}
