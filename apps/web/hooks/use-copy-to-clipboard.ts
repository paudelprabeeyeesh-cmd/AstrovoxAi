"use client"

import { useState, useCallback } from "react"

export function useCopyToClipboard(delay: number = 2000) {
  const [isCopied, setIsCopied] = useState(false)

  const copy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setIsCopied(true)
      setTimeout(() => setIsCopied(false), delay)
    } catch (err) {
      console.error("Failed to copy text: ", err)
    }
  }, [delay])

  return { isCopied, copy }
}
