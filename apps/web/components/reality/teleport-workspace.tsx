'use client'

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function TeleportWorkspace({ children, name }: { children: React.ReactNode; name: string }) {
  const teleport = useRealityStore((s) => s.mode === 'teleport')
  const [visible, setVisible] = useState(true)

  const handleTeleport = () => {
    if (!teleport) return
    setVisible(false)
    setTimeout(() => setVisible(true), 600)
  }

  return (
    <div className="relative">
      <button
        onClick={handleTeleport}
        className="mb-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/70 hover:bg-white/10"
      >
        Teleport {name}
      </button>
      <AnimatePresence mode="wait">
        {visible && (
          <motion.div
            key={name}
            initial={teleport ? { opacity: 0, scale: 0.6, rotateY: 90, filter: 'blur(8px)' } : { opacity: 1 }}
            animate={{ opacity: 1, scale: 1, rotateY: 0, filter: 'blur(0px)' }}
            exit={teleport ? { opacity: 0, scale: 1.4, rotateY: -90, filter: 'blur(8px)' } : { opacity: 0 }}
            transition={{ duration: 0.6, ease: 'easeInOut' }}
            className="relative"
          >
            {children}
            {teleport && (
              <motion.div
                className="pointer-events-none absolute inset-0 rounded-xl border border-cyan-400/40"
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
