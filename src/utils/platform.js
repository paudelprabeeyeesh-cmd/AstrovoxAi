export function detectPlatform() {
  const ua = navigator.userAgent || ''
  if (/Electron|Tauri/i.test(ua)) return 'desktop'
  if (/ReactNative|Mobile/i.test(ua)) return 'mobile'
  if (/Chrome|Firefox|Safari|Edg/i.test(ua)) return 'web'
  return 'unknown'
}

export function isMobile() {
  return /Android|iPhone|iPad|iPod|Opera Mini|IEMobile|WPDesktop/i.test(navigator.userAgent) || window.innerWidth < 768
}

export function isDesktop() {
  return !isMobile() && !('ongesturestart' in window)
}

export function isOnline() {
  return navigator.onLine
}

export function supportsServiceWorker() {
  return 'serviceWorker' in navigator
}

export function supportsPush() {
  return 'PushManager' in window && 'Notification' in window
}

export function supportsShare() {
  return !!navigator.share
}

export function getDeviceType() {
  const width = window.innerWidth
  if (width < 640) return 'phone'
  if (width < 1024) return 'tablet'
  return 'desktop'
}
