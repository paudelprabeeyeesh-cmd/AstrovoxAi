import { useState, useEffect, useCallback } from 'react'
import { Platform, Alert, AppState } from 'react-native'
import * as Notifications from 'expo-notifications'
import * as Device from 'expo-device'
import Constants from 'expo-constants'
import { createRNStorage, createSecureStorage } from './storageAdapter'

const RN_STORAGE = createRNStorage('push')
const SECURE_STORAGE = createSecureStorage('push')

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true
  })
})

export function usePushNotifications() {
  const [permission, setPermission] = useState(null)
  const [token, setToken] = useState(null)
  const [supported, setSupported] = useState(false)
  const [expoPushToken, setExpoPushToken] = useState(null)
  const [notificationListener, setNotificationListener] = useState(null)
  const [responseListener, setResponseListener] = useState(null)

  useEffect(() => {
    setSupported(Device.isDevice)

    async function setup() {
      if (!Device.isDevice) return

      const existingPermission = await RN_STORAGE.get('permission_status')
      if (existingPermission) {
        setPermission(existingPermission)
      }

      const savedToken = await SECURE_STORAGE.get('expo_push_token')
      if (savedToken) {
        setExpoPushToken(savedToken)
      }

      if (existingPermission === true) {
        registerForPushNotifications()
      }
    }

    setup()

    const receivedSub = Notifications.addNotificationReceivedListener(notification => {
      console.log('[Push] Notification received:', notification)
    })

    const responseSub = Notifications.addNotificationResponseReceivedListener(response => {
      console.log('[Push] Notification tapped:', response)
      const data = response.notification.request.content.data
      if (data?.deepLink) {
        handleDeepLink(data.deepLink)
      }
    })

    const appStateSub = AppState.addEventListener('change', nextState => {
      if (nextState === 'active') {
        Notifications.setNotificationBadgeCountAsync(0)
      }
    })

    setNotificationListener(receivedSub)
    setResponseListener(responseSub)

    return () => {
      receivedSub.remove()
      responseSub.remove()
      appStateSub.remove()
    }
  }, [])

  const requestPermission = useCallback(async () => {
    if (!Device.isDevice) {
      return { granted: false, reason: 'Push notifications require a physical device' }
    }

    try {
      const { status: existingStatus } = await Notifications.getPermissionsAsync()
      let finalStatus = existingStatus

      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync()
        finalStatus = status
      }

      setPermission(finalStatus === 'granted')
      await RN_STORAGE.set('permission_status', finalStatus === 'granted')

      if (finalStatus === 'granted') {
        const pushToken = await registerForPushNotifications()
        if (pushToken) {
          await registerPushTokenWithBackend(pushToken)
        }
        return { granted: true, token: pushToken }
      }

      return { granted: false, reason: 'Permission denied' }
    } catch (e) {
      return { granted: false, reason: e.message }
    }
  }, [])

  const registerForPushNotifications = useCallback(async () => {
    try {
      let token

      if (Platform.OS === 'android') {
        await Notifications.setNotificationChannelAsync('default', {
          name: 'default',
          importance: Notifications.AndroidImportance.MAX,
          vibrationPattern: [0, 250, 250, 250],
          lightColor: '#06b6d4'
        })
      }

      token = (await Notifications.getExpoPushTokenAsync({
        projectId: Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId
      })).data

      setExpoPushToken(token)
      await SECURE_STORAGE.set('expo_push_token', token)
      return token
    } catch (e) {
      console.error('Push token registration failed:', e)
      return null
    }
  }, [])

  const registerPushTokenWithBackend = useCallback(async (pushToken) => {
    try {
      const token = await RN_STORAGE.get('auth_token')
      if (!token) return

      await fetch('https://api.astrovox.ai/v1/push/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          push_token: pushToken,
          platform: Platform.OS,
          device: Device.modelName
        })
      })
    } catch (e) {
      console.error('Backend push registration failed:', e)
    }
  }, [])

  const unsubscribe = useCallback(async () => {
    try {
      await Notifications.cancelAllScheduledNotificationsAsync()
      await Notifications.setNotificationBadgeCountAsync(0)
      await SECURE_STORAGE.remove('expo_push_token')
      setExpoPushToken(null)
      setPermission(false)
      await RN_STORAGE.set('permission_status', false)
      return true
    } catch (e) {
      console.error('Push unsubscribe failed:', e)
      return false
    }
  }, [])

  const showLocalNotification = useCallback(async (title, options = {}) => {
    try {
      const notificationId = await Notifications.scheduleNotificationAsync({
        content: {
          title,
          body: options.body || '',
          data: options.data || {},
          sound: options.sound || 'default',
          badge: options.badge ?? 1,
          priority: Notifications.AndroidNotificationPriority.HIGH
        },
        trigger: options.trigger || null
      })
      return notificationId
    } catch (e) {
      console.error('Local notification failed:', e)
      return null
    }
  }, [])

  return {
    supported,
    permission,
    token,
    expoPushToken,
    requestPermission,
    registerForPushNotifications,
    unsubscribe,
    showLocalNotification
  }
}

function handleDeepLink(url) {
  console.log('[Push] Deep link:', url)
}

export function PushNotificationAdapter() {
  const { requestPermission } = usePushNotifications()

  useEffect(() => {
    requestPermission()
  }, [])

  return null
}
