'use client'

import { motion } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function MultiverseSync({ children, className }: { children: React.ReactNode; className?: string }) {
  const snapshots = useRealityStore((s) => s.multiverseSnapshots)
  const restoreMultiverseSnapshot = useRealityStore((s) => s.restoreMultiverseSnapshot)

  return (
    <div className={className}>
      {children}
      {snapshots.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {snapshots.map((_, idx) => (
            <motion.button
              key={idx}
              className="rounded-lg border border-white/20 bg-white/5 px-2 py-1 text-[10px] text-white hover:bg-white/10"
              whileHover={{ scale: 1.05 }}
              onClick={() => restoreMultiverseSnapshot(idx)}
            >
              Restore #{idx + 1}
            </motion.button>
          ))}
        </div>
      )}
    </div>
  )
}
