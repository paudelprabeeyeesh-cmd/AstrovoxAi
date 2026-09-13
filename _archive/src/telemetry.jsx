import { useState, useEffect } from 'react'
import { supabase } from './supabase'

// Get API base URL from environment or use default
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Get current auth token
 */
async function getAuthToken() {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token || null
}

/**
 * Send event to backend telemetry API
 */
async function sendToBackend(endpoint, payload) {
  try {
    const token = await getAuthToken()
    if (!token) {
      console.warn('[telemetry] No auth token available, event not sent to backend')
      return
    }

    const response = await fetch(`${API_BASE_URL}/telemetry${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      console.warn(`[telemetry] Backend request failed: ${response.status}`)
    }
  } catch (error) {
    console.warn('[telemetry] Failed to send event to backend:', error.message)
  }
}

/**
 * Track an event with payload
 * @param {String} eventName - Name of the event
 * @param {Object} payload - Event data
 */
export async function trackEvent(eventName, payload = {}) {
  if (typeof window === 'undefined') return
  
  if (!eventName || typeof eventName !== 'string') {
    console.warn('Invalid event name:', eventName)
    return
  }

  const safePayload = payload && typeof payload === 'object' ? payload : {}
  const timestamp = new Date().toISOString()
  
  console.info(`[telemetry] ${eventName}`, {
    timestamp,
    ...safePayload
  })

  // Send to backend
  await sendToBackend('/event', {
    event_name: eventName,
    category: 'general',
    metadata: safePayload,
    timestamp
  })
}

/**
 * Log an event (alias for trackEvent)
 * @param {String} eventName - Name of the event
 * @param {Object} payload - Event data
 */
export async function logEvent(eventName, payload = {}) {
  return trackEvent(eventName, payload)
}

/**
 * Track page view
 * @param {String} pageName - Name of the page
 */
export async function trackPageView(pageName) {
  trackEvent('page_view', { page: pageName })
  
  // Also send to backend
  await sendToBackend('/page-view', {
    page: pageName,
    referrer: document.referrer || null
  })
}

/**
 * Track user action
 * @param {String} action - Action name
 * @param {String} category - Category of action
 * @param {Object} metadata - Additional metadata
 */
export async function trackUserAction(action, category = 'user', metadata = {}) {
  trackEvent('user_action', {
    action,
    category,
    ...metadata
  })
  
  // Also send to backend
  await sendToBackend('/user-action', {
    action,
    category,
    metadata
  })
}

/**
 * Track error event
 * @param {String} errorName - Error name
 * @param {String} errorMessage - Error message
 * @param {Object} context - Error context
 */
export async function trackError(errorName, errorMessage, context = {}) {
  trackEvent('error', {
    errorName,
    errorMessage,
    ...context
  })
  
  // Also send to backend
  await sendToBackend('/error', {
    error_name: errorName,
    error_message: errorMessage,
    stack_trace: context.stackTrace || null,
    context: context || {}
  })
}

/**
 * Get telemetry statistics for current user
 */
export async function getTelemetryStats(limit = 100, offset = 0) {
  try {
    const token = await getAuthToken()
    if (!token) {
      console.warn('[telemetry] No auth token available')
      return null
    }

    const response = await fetch(
      `${API_BASE_URL}/telemetry/stats?limit=${limit}&offset=${offset}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    )

    if (!response.ok) {
      console.warn(`[telemetry] Failed to fetch stats: ${response.status}`)
      return null
    }

    return await response.json()
  } catch (error) {
    console.warn('[telemetry] Failed to fetch stats:', error.message)
    return null
  }
}

export default function Telemetry({ totalPackets, dbStatus }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    trackPageView('dashboard')
  }, [])

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await getTelemetryStats(50, 0)
        setStats(data)
      } catch (err) {
        console.error('Failed to load telemetry stats:', err)
      } finally {
        setLoading(false)
      }
    }
    loadStats()
  }, [])

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '8px',
      padding: '12px',
      backgroundColor: 'rgba(4, 8, 20, 0.5)',
      border: '1px solid #1e293b',
      borderRadius: '12px',
      backdropFilter: 'blur(8px)'
    }}>
      <h3 style={{
        margin: '0 0 8px 0',
        fontSize: '12px',
        color: '#67e8f9',
        letterSpacing: '1px',
        fontWeight: '600'
      }}>
        📡 TELEMETRY
      </h3>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '8px',
        fontSize: '11px'
      }}>
        <div style={{ color: '#94a3b8' }}>
          <span style={{ color: '#34d399' }}>●</span> DB: {dbStatus}
        </div>
        <div style={{ color: '#94a3b8' }}>
          Packets: {totalPackets || 0}
        </div>
        <div style={{ color: '#94a3b8' }}>
          Events: {loading ? '...' : (stats?.total_events || 0)}
        </div>
        <div style={{ color: '#94a3b8' }}>
          Errors: {loading ? '...' : (stats?.error_count || 0)}
        </div>
      </div>
    </div>
  )
}
