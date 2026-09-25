'use client'

import { useRef, useEffect } from 'react'
import { useMotionValue, useSpring } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function PhysicsDefyingInteraction({ children, className }: { children: React.ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const rotateX = useSpring(useMotionValue(0), { stiffness: 200, damping: 20 })
  const rotateY = useSpring(useMotionValue(0), { stiffness: 200, damping: 20 })

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      const dx = (e.clientX - centerX) / (rect.width / 2)
      const dy = (e.clientY - centerY) / (rect.height / 2)
      rotateX.set(-dy * 10)
      rotateY.set(dx * 10)
    }
    const reset = () => { rotateX.set(0); rotateY.set(0) }
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseleave', reset)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseleave', reset)
    }
  }, [rotateX, rotateY])

  return (
    <div
      ref={ref}
      className={className}
      style={{
        transform: `perspective(800px) rotateX(${rotateX.get()}deg) rotateY(${rotateY.get()}deg)`,
        transition: 'transform 0.1s ease-out',
      }}
    >
      {children}
    </div>
  )
}
