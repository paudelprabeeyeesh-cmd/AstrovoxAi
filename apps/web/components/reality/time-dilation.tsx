'use client'

import { useEffect, useRef } from 'react'
import { useRealityStore } from '@/lib/store/reality-store'

export function useTimeDilation() {
  const timeDilation = useRealityStore((s) => s.timeDilation)
  const root = useRef<HTMLElement | null>(null)

  useEffect(() => {
    root.current = document.documentElement
    if (!root.current) return
    root.current.style.setProperty('--reality-time-dilation', String(timeDilation))
    root.current.style.setProperty('animation-duration', `${1 / timeDilation}s`)
    root.current.style.setProperty('transition-duration', `${0.3 / timeDilation}s`)
  }, [timeDilation])
}

export function TimeDilatedAnimation({ children, className }: { children: React.ReactNode; className?: string }) {
  useTimeDilation()
  const timeDilation = useRealityStore((s) => s.timeDilation)
  const duration = 1 / timeDilation

  return (
    <div
      className={className}
      style={
        {
          '--td-duration': `${duration}s`,
          animationDuration: `var(--td-duration)`,
        } as React.CSSProperties
      }
    >
      {children}
    </div>
  )
}
