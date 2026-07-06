export function trackEvent(eventName, payload = {}) {
  if (typeof window === 'undefined') return;
  const safePayload = payload && typeof payload === 'object' ? payload : {};
  console.info(`[telemetry] ${eventName}`, safePayload);
}

export function logEvent(eventName, payload = {}) {
  trackEvent(eventName, payload);
}

export default {
  trackEvent,
  logEvent,
};