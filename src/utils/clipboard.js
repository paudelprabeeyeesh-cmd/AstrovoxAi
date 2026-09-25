import { useState, useCallback } from 'react'

export async function copyToClipboard(text) {
  if (typeof navigator === 'undefined' || !navigator.clipboard) {
    return fallbackCopy(text)
  }
  try {
    await navigator.clipboard.writeText(text)
    return { success: true }
  } catch (err) {
    return fallbackCopy(text)
  }
}

async function fallbackCopy(text) {
  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)
    return { success: successful }
  } catch (err) {
    return { success: false, error: err }
  }
}

export function useClipboard() {
  const [copied, setCopied] = useState(false)

  const copy = useCallback(async (text) => {
    const result = await copyToClipboard(text)
    if (result.success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
    return result
  }, [])

  return { copied, copy }
}
