/**
 * Telemetry and event tracking module
 * Provides centralized event tracking functionality
 */

/**
 * Track an event with payload
 * @param {String} eventName - Name of the event
 * @param {Object} payload - Event data
 */
export function trackEvent(eventName, payload = {}) {
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
}

/**
 * Log an event (alias for trackEvent)
 * @param {String} eventName - Name of the event
 * @param {Object} payload - Event data
 */
export function logEvent(eventName, payload = {}) {
  trackEvent(eventName, payload)
}

/**
 * Track page view
 * @param {String} pageName - Name of the page
 */
export function trackPageView(pageName) {
  trackEvent('page_view', { page: pageName })
}

/**
 * Track user action
 * @param {String} action - Action name
 * @param {String} category - Category of action
 * @param {Object} metadata - Additional metadata
 */
export function trackUserAction(action, category = 'user', metadata = {}) {
  trackEvent('user_action', {
    action,
    category,
    ...metadata
  })
}

/**
 * Track error event
 * @param {String} errorName - Error name
 * @param {String} errorMessage - Error message
 * @param {Object} context - Error context
 */
export function trackError(errorName, errorMessage, context = {}) {
  trackEvent('error', {
    errorName,
    errorMessage,
    ...context
  })
}

export default {
  trackEvent,
  logEvent,
  trackPageView,
  trackUserAction,
  trackError
}
