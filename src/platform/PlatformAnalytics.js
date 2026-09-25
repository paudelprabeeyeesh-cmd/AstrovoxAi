import { useState, useEffect, useCallback } from 'react'
import { createStorage } from '../utils/storage'
import { isOnline, detectPlatform, getDeviceType } from '../utils/platform'

const ANALYTICS_STORAGE = createStorage('analytics')
const ANALYTICS_QUEUE_KEY = 'astrovox-analytics-queue'
const MAX_QUEUE_SIZE = 50

export class PlatformAnalytics {
  constructor(config = {}) {
    this.apiKey = config.apiKey || ''
    this.apiBase = config.apiBase || '/api/analytics'
    this.queue = []
    this.enabled = config.enabled !== false
    this.debug = config.debug || false
    this.platform = detectPlatform()
    this.deviceType = getDeviceType()
  }

  track(eventName, properties = {}) {
    if (!this.enabled) return

    const event = {
      id: crypto.randomUUID?.() || `${Date.now()}-${Math.random()}`,
      event: eventName,
      properties: {
        ...properties,
        platform: this.platform,
        device_type: this.deviceType,
        user_agent: navigator.userAgent,
        viewport_width: window.innerWidth,
        viewport_height: window.innerHeight,
        language: navigator.language,
        online: isOnline(),
        timestamp: new Date().toISOString()
      },
      createdAt: new Date().toISOString()
    }

    this.queue.push(event)
    this.persistQueue()

    if (this.debug) {
      console.log('[Analytics]', eventName, event.properties)
    }

    if (this.queue.length >= MAX_QUEUE_SIZE) {
      this.flush()
    }
  }

  page(viewName, properties = {}) {
    this.track('page_view', {
      view_name: viewName,
      ...properties
    })
  }

  identify(userId, traits = {}) {
    this.track('user_identify', {
      user_id: userId,
      traits
    })
  }

  async flush() {
    if (this.queue.length === 0) return

    const events = [...this.queue]
    this.queue = []

    try {
      const response = await fetch(this.apiBase + '/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({ events, source: 'web' })
      })

      if (!response.ok) {
        throw new Error(`Analytics flush failed: ${response.status}`)
      }

      this.persistQueue()
    } catch (e) {
      this.queue.unshift(...events)
      this.persistQueue()
      console.error('Analytics flush error:', e)
    }
  }

  persistQueue() {
    try {
      ANALYTICS_STORAGE.set(ANALYTICS_QUEUE_KEY, this.queue.slice(-MAX_QUEUE_SIZE))
    } catch {
      console.warn('Analytics persistence failed')
    }
  }

  loadQueue() {
    try {
      const saved = ANALYTICS_STORAGE.get(ANALYTICS_QUEUE_KEY)
      if (Array.isArray(saved)) {
        this.queue = saved.slice(-MAX_QUEUE_SIZE)
      }
    } catch {
      this.queue = []
    }
  }

  clear() {
    this.queue = []
    ANALYTICS_STORAGE.remove(ANALYTICS_QUEUE_KEY)
  }
}

export function usePlatformAnalytics(config = {}) {
  const [analytics] = useState(() => new PlatformAnalytics(config))
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID?.() || `${Date.now()}`)

  useEffect(() => {
    analytics.loadQueue()

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        analytics.flush()
      }
    }

    const handleBeforeUnload = () => {
      analytics.flush()
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('beforeunload', handleBeforeUnload)

    const interval = setInterval(() => {
      if (analytics.queue.length > 0) {
        analytics.flush()
      }
    }, 30000)

    analytics.page('app_loaded', { session_id: sessionId })

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('beforeunload', handleBeforeUnload)
      clearInterval(interval)
      analytics.flush()
    }
  }, [analytics, sessionId])

  const track = useCallback((eventName, properties) => {
    analytics.track(eventName, { session_id: sessionId, ...properties })
  }, [analytics, sessionId])

  const page = useCallback((viewName, properties) => {
    analytics.page(viewName, { session_id: sessionId, ...properties })
  }, [analytics, sessionId])

  const identify = useCallback((userId, traits) => {
    analytics.identify(userId, { session_id: sessionId, ...traits })
  }, [analytics, sessionId])

  const flush = useCallback(() => analytics.flush(), [analytics])

  const clear = useCallback(() => analytics.clear(), [analytics])

  return {
    track,
    page,
    identify,
    flush,
    clear,
    sessionId,
    queueSize: analytics.queue.length
  }
}

export function PlatformAnalyticsWrapper({ config, children }) {
  const { track, page, flush } = usePlatformAnalytics(config)

  return children({ track, page, flush })
}
