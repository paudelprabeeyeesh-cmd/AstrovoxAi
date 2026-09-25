import { useState, useCallback } from 'react'
import { createStorage } from '../utils/storage'
import { supportsShare } from '../utils/platform'

const SHARE_STORAGE = createStorage('share')

export function useShareTarget() {
  const [sharedData, setSharedData] = useState(null)
  const [sharedText, setSharedText] = useState('')
  const [sharedUrl, setSharedUrl] = useState('')
  const [sharedTitle, setSharedTitle] = useState('')
  const [supported, setSupported] = useState(false)

  useState(() => {
    setSupported(supportsShare())
  }, [])

  const handleShare = useCallback(async (data) => {
    const { title, text, url, files } = data

    setSharedTitle(title || '')
    setSharedText(text || '')
    setSharedUrl(url || '')
    setSharedData({ title, text, url, files })

    SHARE_STORAGE.set('last_shared', {
      title,
      text,
      url,
      files: files ? files.map(f => f.name) : [],
      timestamp: new Date().toISOString()
    })

    if (text) {
      setSharedText(text)
    }
    if (url) {
      setSharedUrl(url)
    }

    return { title, text, url, files }
  }, [])

  const clearSharedData = useCallback(() => {
    setSharedData(null)
    setSharedText('')
    setSharedUrl('')
    setSharedTitle('')
    SHARE_STORAGE.remove('last_shared')
  }, [])

  const shareFromApp = useCallback(async (data) => {
    if (!supported) {
      console.warn('Web Share API not supported')
      return { shared: false }
    }

    try {
      const shareData = {
        title: data.title || 'Astrovox AI',
        text: data.text || '',
        url: data.url || window.location.href
      }

      if (data.files && data.files.length > 0) {
        shareData.files = data.files
      }

      await navigator.share(shareData)
      return { shared: true }
    } catch (e) {
      if (e.name !== 'AbortError') {
        console.error('Share failed:', e)
      }
      return { shared: false, error: e.message }
    }
  }, [supported])

  return {
    sharedData,
    sharedText,
    sharedUrl,
    sharedTitle,
    supported,
    handleShare,
    clearSharedData,
    shareFromApp,
    getLastShared: () => SHARE_STORAGE.get('last_shared')
  }
}

export function ShareTargetHandler({ onShareReceived }) {
  const { handleShare, supported } = useShareTarget()

  useState(() => {
    if (!supported) return

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        const params = new URLSearchParams(window.location.search)
        const title = params.get('title')
        const text = params.get('text')
        const url = params.get('url')

        if (title || text || url) {
          handleShare({ title, text, url })
          onShareReceived?.({ title, text, url })
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('load', handleVisibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('load', handleVisibilityChange)
    }
  })

  return null
}

export function ShareButton({ content, onShareStart, onShareEnd }) {
  const { shareFromApp, supported } = useShareTarget()

  const handleClick = async () => {
    if (!supported) {
      onShareEnd?.({ shared: false, error: 'Web Share API not supported' })
      return
    }

    onShareStart?.()
    const result = await shareFromApp(content)
    onShareEnd?.(result)
  }

  if (!supported) return null

  return (
    <button
      onClick={handleClick}
      style={{
        padding: '8px 16px',
        background: 'rgba(6, 182, 212, 0.1)',
        border: '1px solid #06b6d4',
        color: '#06b6d4',
        borderRadius: 8,
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: 600
      }}
    >
      Share
    </button>
  )
}
