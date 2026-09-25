'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useChatStore } from '@/lib/store/chat-store'
import { useRealityStore } from '@/lib/store/reality-store'
import { cn } from '@/lib/utils'

export function WormholeNav({ onSelect }: { onSelect?: (id: string) => void }) {
  const conversations = useChatStore((s) => s.conversations)
  const activeId = useChatStore((s) => s.activeId)
  const wormhole = useRealityStore((s) => s.mode === 'wormhole')

  return (
    <div className="relative h-64 w-full overflow-hidden rounded-2xl border border-white/10 bg-black/40">
      <AnimatePresence>
        {wormhole && (
          <motion.div
            className="absolute inset-0"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 1.2 }}
            transition={{ duration: 0.6 }}
          >
            <div className="flex h-full items-center justify-center gap-4 overflow-hidden">
              {conversations.map((c, idx) => (
                <motion.button
                  key={c.id}
                  className={cn(
                    'relative h-32 w-24 shrink-0 rounded-xl border text-left text-white',
                    activeId === c.id ? 'border-white bg-white/10' : 'border-white/20 bg-white/5'
                  )}
                  initial={{ y: 300, opacity: 0, rotateX: 45 }}
                  animate={{ y: 0, opacity: 1, rotateX: 0 }}
                  transition={{ delay: idx * 0.08, type: 'spring', stiffness: 120, damping: 14 }}
                  whileHover={{ scale: 1.05, y: -8 }}
                  onClick={() => onSelect?.(c.id)}
                >
                  <div className="p-2">
                    <div className="truncate text-xs font-medium">{c.title}</div>
                    <div className="mt-1 text-[10px] text-white/60">{c.messages?.length ?? 0} msgs</div>
                  </div>
                  <motion.div
                    className="absolute inset-0 rounded-xl bg-gradient-to-t from-purple-500/40 to-transparent"
                    animate={{ opacity: [0.2, 0.6, 0.2] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  />
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      {!wormhole && (
        <div className="flex h-full items-center justify-center text-xs text-white/50">
          Enable wormhole mode to warp between conversations
        </div>
      )}
    </div>
  )
}
