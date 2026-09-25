'use client'

import { useRef, useState } from 'react'
import { motion, useMotionValue, useSpring } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function CloneDuplicate({ children, className }: { children: React.ReactNode; className?: string }) {
  const cloneCount = useRealityStore((s) => s.cloneCount)
  const [clones, setClones] = useState<{ id: number; x: number; y: number }[]>([])
  const rootRef = useRef<HTMLDivElement>(null)

  const spawnClone = () => {
    if (!rootRef.current) return
    const rect = rootRef.current.getBoundingClientRect()
    const x = (Math.random() - 0.5) * 200
    const y = (Math.random() - 0.5) * 200
    setClones((prev) => [...prev.slice(-8), { id: Date.now(), x, y }])
  }

  return (
    <div ref={rootRef} className={className} style={{ position: 'relative' }}>
      {children}
      {Array.from({ length: Math.max(0, cloneCount - 1) }).map((_, i) => (
        <motion.div
          key={clones[i]?.id ?? i}
          className="pointer-events-none absolute inset-0"
          style={{ x: clones[i]?.x ?? 0, y: clones[i]?.y ?? 0 }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 0.6, scale: 1 }}
          transition={{ delay: i * 0.05 }}
        >
          {children}
        </motion.div>
      ))}
      <button
        onClick={spawnClone}
        className="absolute -right-8 top-0 rounded border border-white/20 bg-white/10 px-2 py-1 text-[10px] text-white hover:bg-white/20"
      >
        Clone
      </button>
    </div>
  )
}
