import { useState, useCallback } from 'react'
import { Platform, Share as RNShare, Alert } from 'react-native'
import { createRNStorage } from '../mobile/storageAdapter'

const SHARE_STORAGE = createRNStorage('share')

export function useShareTarget() {
  const [sharedData, setSharedData] = useState(null)
  const [sharedText, setSharedText] = useState('')
  const [sharedUrl, setSharedUrl] = useState('')
  const [sharedTitle, setSharedTitle] = useState('')

  const handleShare = useCallback(async (data) => {
    const { title, text, url, files } = data

    setSharedTitle(title || '')
    setSharedText(text || '')
    setSharedUrl(url || '')
    setSharedData({ title, text, url, files })

    await SHARE_STORAGE.set('last_shared', {
      title,
      text,
      url,
      files: files ? files.map(f => f.name || f) : [],
      timestamp: new Date().toISOString()
    })

    return { title, text, url, files }
  }, [])

  const clearSharedData = useCallback(async () => {
    setSharedData(null)
    setSharedText('')
    setSharedUrl('')
    setSharedTitle('')
    await SHARE_STORAGE.remove('last_shared')
  }, [])

  const shareFromApp = useCallback(async (data) => {
    try {
      const shareData = {
        title: data.title || 'Astrovox AI',
        message: data.text || '',
        url: data.url || ''
      }

      if (Platform.OS === 'ios' && data.files?.length > 0) {
        shareData.urls = data.files.map(f => typeof f === 'string' ? f : f.uri)
      }

      await RNShare.share(shareData)
      return { shared: true }
    } catch (e) {
      if (e.name !== 'AbortError') {
        console.error('Share failed:', e)
      }
      return { shared: false, error: e.message }
    }
  }, [])

  const getLastShared = useCallback(async () => {
    return await SHARE_STORAGE.get('last_shared')
  }, [])

  return {
    sharedData,
    sharedText,
    sharedUrl,
    sharedTitle,
    handleShare,
    clearSharedData,
    shareFromApp,
    getLastShared
  }
}

export function ShareTargetHandler({ onShareReceived }) {
  const { handleShare } = useShareTarget()

  useEffect(() => {
    async function checkInitialShare() {
      try {
        const lastShared = await SHARE_STORAGE.get('last_shared')
        if (lastShared) {
          onShareReceived?.(lastShared)
        }
      } catch (e) {
        console.error('Share target init failed:', e)
      }
    }

    checkInitialShare()
  }, [onShareReceived])

  return null
}

export function ShareButton({ content, onShareStart, onShareEnd }) {
  const { shareFromApp } = useShareTarget()

  const handlePress = async () => {
    if (!content) return
    onShareStart?.()
    const result = await shareFromApp(content)
    onShareEnd?.(result)
  }

  return null
}
