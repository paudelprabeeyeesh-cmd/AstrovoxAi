'use client'

import { motion, useSpring, useMotionValue } from 'framer-motion'
import { useRef, useEffect } from 'react'
import { useRealityStore } from '@/lib/store/reality-store'

export function GravityPanel({ children, className }: { children: React.ReactNode; className?: string }) {
  const gravityEnabled = useRealityStore((s) => s.gravityEnabled)
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const springX = useSpring(x, { stiffness: 120, damping: 14 })
  const springY = useSpring(y, { stiffness: 120, damping: 14 })

  useEffect(() => {
    if (!gravityEnabled || !ref.current) return
    const el = ref.current
    const handleMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      const dx = (e.clientX - centerX) / (rect.width / 2)
      const dy = (e.clientY - centerY) / (rect.height / 2)
      x.set(dy * 18)
      y.set(-dx * 18)
    }
    const reset = () => { x.set(0); y.set(0) }
    window.addEventListener('mousemove', handleMove)
    window.addEventListener('mouseleave', reset)
    return () => {
      window.removeEventListener('mousemove', handleMove)
      window.removeEventListener('mouseleave', reset)
    }
  }, [gravityEnabled, x, y])

  return (
    <motion.div
      ref={ref}
      style={{ x: springX, y: springY }}
      className={className}
      transition={{ type: 'spring', stiffness: 120, damping: 14 }}
    >
      {children}
    </motion.div>
  )
}
