'use client'

import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useRealityStore } from '@/lib/store/reality-store'

export function UniverseInABox({ title, children }: { title: string; children: React.ReactNode }) {
  const sandbox = useRealityStore((s) => s.mode === 'sandbox')
  const [open, setOpen] = useState(false)
  const [env, setEnv] = useState<string | null>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const launchSandbox = () => {
    setEnv(title)
    setOpen(true)
  }

  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium text-white">{title}</div>
          <div className="text-xs text-white/60">Sandboxed reality container</div>
        </div>
        <button
          onClick={launchSandbox}
          className="rounded-lg border border-white/20 bg-white/10 px-3 py-1 text-xs text-white hover:bg-white/20"
        >
          Open Universe
        </button>
      </div>
      <AnimatePresence>
        {open && env && (
          <motion.div
            className="mt-4 overflow-hidden rounded-xl border border-white/10"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
          >
            <div className="flex items-center justify-between border-b border-white/10 bg-black/40 px-3 py-2">
              <span className="text-xs text-white/80">Universe: {env}</span>
              <button onClick={() => setOpen(false)} className="text-xs text-white/60 hover:text-white">
                Close
              </button>
            </div>
            <div className="relative h-64 w-full bg-black">
              <iframe
                ref={iframeRef}
                title={env}
                sandbox="allow-scripts allow-same-origin"
                srcDoc={sandbox ? generateSandboxHTML(env) : generateSandboxHTML(env)}
                className="h-full w-full border-0"
              />
              {sandbox && (
                <motion.div
                  className="pointer-events-none absolute inset-0 border-2 border-purple-500/50"
                  animate={{ opacity: [0.2, 0.8, 0.2] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function generateSandboxHTML(title: string) {
  return `<!DOCTYPE html><html><head><style>
    body{margin:0;background:#000;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;overflow:hidden;}
    .box{width:120px;height:120px;background:linear-gradient(135deg,#7c3aed,#06b6d4);border-radius:24px;animation:pulse 3s infinite;}
    @keyframes pulse{0%,100%{transform:scale(1);}50%{transform:scale(1.15);}}
  </style></head><body><div class="box"></div><script>console.log('Universe ${title} initialized');</script></body></html>`
}
