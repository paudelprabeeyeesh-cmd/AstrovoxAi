import { useEffect, useCallback } from 'react'
import { Linking, Platform } from 'react-native'
import * as IntentLauncher from 'expo-intent-launcher'
import { createRNStorage } from './storageAdapter'

const LINK_STORAGE = createRNStorage('deep_links')

const ROUTE_MAP = {
  '/chat': 'chat',
  '/memory': 'memory',
  '/settings': 'settings',
  '/dashboard': 'chat',
  '/conversation': 'conversation',
  '/reset-password': 'reset-password'
}

const UNIVERSAL_LINKS = {
  ios: 'https://astrovox.ai',
  android: 'https://astrovox.ai'
}

export function useDeepLinking(onNavigate) {
  const handleRoute = useCallback((path, params = {}) => {
    const cleanPath = path.split('?')[0]
    const route = ROUTE_MAP[cleanPath] || 'chat'
    const urlParams = new URLSearchParams(path.split('?')[1] || '')

    const parsed = { route }
    if (route === 'conversation') {
      parsed.conversationId = params.id || urlParams.get('id')
    } else if (route === 'reset-password') {
      parsed.accessToken = params.access_token || urlParams.get('access_token')
      parsed.refreshToken = params.refresh_token || urlParams.get('refresh_token')
    } else {
      Object.entries(params).forEach(([key, value]) => {
        if (value) parsed[key] = value
      })
    }

    onNavigate?.(parsed)

    LINK_STORAGE.set('last_route', {
      path,
      route,
      params: parsed,
      timestamp: new Date().toISOString()
    })
  }, [onNavigate])

  useEffect(() => {
    async function handleInitialLink() {
      try {
        const initialUrl = await Linking.getInitialURL()
        if (initialUrl) {
          parseIncomingLink(initialUrl)
        }
      } catch (e) {
        console.error('Failed to get initial URL:', e)
      }
    }

    handleInitialLink()

    const subscription = Linking.addEventListener('url', ({ url }) => {
      parseIncomingLink(url)
    })

    return () => subscription.remove()
  }, [])

  const parseIncomingLink = useCallback((url) => {
    try {
      const urlObj = new URL(url)
      const path = urlObj.pathname
      const params = Object.fromEntries(urlObj.searchParams.entries())
      handleRoute(path + urlObj.search, params)
    } catch {
      console.error('Failed to parse deep link:', url)
    }
  }, [handleRoute])

  const generateLink = useCallback((route, params = {}) => {
    const baseUrl = UNIVERSAL_LINKS[Platform.OS] || 'https://astrovox.ai'
    const searchParams = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, value)
      }
    })

    const queryString = searchParams.toString()
    return `${baseUrl}${route}${queryString ? '?' + queryString : ''}`
  }, [])

  const openDeepLink = useCallback(async (route, params = {}) => {
    const url = generateLink(route, params)
    try {
      const supported = await Linking.canOpenURL(url)
      if (supported) {
        await Linking.openURL(url)
      } else {
        console.warn('Cannot open URL:', url)
      }
    } catch (e) {
      console.error('Failed to open deep link:', e)
    }
  }, [generateLink])

  const openAppSettings = useCallback(async () => {
    try {
      if (Platform.OS === 'ios') {
        await Linking.openURL('app-settings:')
      } else {
        await IntentLauncher.openSettingsAsync()
      }
    } catch (e) {
      console.error('Failed to open settings:', e)
    }
  }, [])

  return {
    handleRoute,
    parseIncomingLink,
    generateLink,
    openDeepLink,
    openAppSettings,
    getLastRoute: () => LINK_STORAGE.get('last_route'),
    routeMap: ROUTE_MAP
  }
}

export function DeepLinkingManager() {
  const { handleRoute } = useDeepLinking(() => {})

  useEffect(() => {
    async function setup() {
      try {
        const initialUrl = await Linking.getInitialURL()
        if (initialUrl) {
          handleRoute(new URL(initialUrl).pathname + new URL(initialUrl).search)
        }
      } catch (e) {
        console.error('Deep linking init failed:', e)
      }
    }

    setup()
  }, [handleRoute])

  return null
}

export function registerDeepLinkHandler() {
  console.log('Deep linking handler registered for', Platform.OS)
}

export function configureUniversalLinks(config = {}) {
  return {
    ios: {
      ...UNIVERSAL_LINKS.ios,
      appId: config.iosAppId || '',
      teamId: config.iosTeamId || ''
    },
    android: {
      ...UNIVERSAL_LINKS.android,
      packageName: config.androidPackageName || 'ai.astrovox.mobile'
    }
  }
}
