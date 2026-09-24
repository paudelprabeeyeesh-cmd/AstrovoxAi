"use client"

import { useEffect } from "react"

export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  modifiers: { ctrl?: boolean; shift?: boolean; alt?: boolean; meta?: boolean } = {}
) {
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const ctrlMatch = modifiers.ctrl ? event.ctrlKey || event.metaKey : !event.ctrlKey && !event.metaKey
      const shiftMatch = modifiers.shift ? event.shiftKey : !event.shiftKey
      const altMatch = modifiers.alt ? event.altKey : !event.altKey

      if (event.key.toLowerCase() === key.toLowerCase() && ctrlMatch && shiftMatch && altMatch) {
        event.preventDefault()
        callback()
      }
    }

    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [key, callback, modifiers])
}
