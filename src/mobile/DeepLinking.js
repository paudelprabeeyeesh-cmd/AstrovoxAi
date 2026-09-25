import { useEffect, useCallback } from 'react'
import { createStorage } from '../utils/storage'

const LINK_STORAGE = createStorage('deep_links')

const ROUTE_MAP = {
  '/chat': 'chat',
  '/memory': 'memory',
  '/settings': 'settings',
  '/dashboard': 'chat',
  '/conversation': 'conversation',
  '/reset-password': 'reset-password'
}

export function useDeepLinking(onNavigate) {
  const handleRoute = useCallback((path) => {
    const cleanPath = path.split('?')[0]
    const route = ROUTE_MAP[cleanPath] || 'chat'
    const params = new URLSearchParams(path.split('?')[1] || '')

    if (route === 'conversation') {
      const conversationId = params.get('id')
      onNavigate?.({ route, conversationId })
    } else if (route === 'reset-password') {
      const accessToken = params.get('access_token')
      const refreshToken = params.get('refresh_token')
      onNavigate?.({ route, accessToken, refreshToken })
    } else {
      onNavigate?.({ route })
    }

    LINK_STORAGE.set('last_route', { path, route, params: Object.fromEntries(params), timestamp: new Date().toISOString() })
  }, [onNavigate])

  useEffect(() => {
    if (!window.location?.pathname) return

    handleRoute(window.location.pathname + window.location.search)

    const handlePopState = () => {
      handleRoute(window.location.pathname + window.location.search)
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [handleRoute])

  const generateLink = useCallback((route, params = {}) => {
    const baseUrl = window.location.origin
    const searchParams = new URLSearchParams()

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, value)
      }
    })

    const queryString = searchParams.toString()
    return `${baseUrl}${route}${queryString ? '?' + queryString : ''}`
  }, [])

  const parseIncomingLink = useCallback((url) => {
    try {
      const urlObj = new URL(url)
      const path = urlObj.pathname
      handleRoute(path + urlObj.search)
    } catch {
      console.error('Failed to parse deep link:', url)
    }
  }, [handleRoute])

  return {
    generateLink,
    parseIncomingLink,
    getLastRoute: () => LINK_STORAGE.get('last_route'),
    routeMap: ROUTE_MAP
  }
}

export function DeepLinkingManager() {
  const handleNavigate = useCallback((nav) => {
    console.log('Navigate:', nav)
  }, [])

  useDeepLinking(handleNavigate)

  useEffect(() => {
    const handleMessage = (event) => {
      if (event.data?.type === 'DEEP_LINK') {
        const url = event.data.url
        if (url) {
          window.history.pushState({}, '', url)
          window.dispatchEvent(new PopStateEvent('popstate'))
        }
      }
    }

    window.addEventListener('message', handleMessage)

    if (window.ReactNativeWebView) {
      window.addEventListener('message', handleMessage)
    }

    return () => window.removeEventListener('message', handleMessage)
  }, [])

  return null
}

export function registerDeepLinkHandler() {
  if (document) {
    document.addEventListener('DOMContentLoaded', () => {
      console.log('Deep linking initialized')
    })
  }
}
