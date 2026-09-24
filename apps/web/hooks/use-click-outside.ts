"use client"

import { useEffect, useRef } from "react"

export function useClickOutside(
  callback: () => void,
  shouldTrigger: boolean = true
) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!shouldTrigger) return

    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        callback()
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    document.addEventListener("touchstart", handleClickOutside)

    return () => {
      document.removeEventListener("mousedown", handleClickOutside)
      document.removeEventListener("touchstart", handleClickOutside)
    }
  }, [callback, shouldTrigger])

  return ref
}
