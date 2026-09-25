'use client'

import { useRealityStore } from '@/lib/store/reality-store'
import { useChatStore } from '@/lib/store/chat-store'
import { useUIStore } from '@/lib/store/ui-store'

export function MetaRealityDebug() {
  const reality = useRealityStore()
  const chat = useChatStore()
  const ui = useUIStore()

  const state = {
    mode: reality.mode,
    gravity: reality.gravityEnabled,
    timeDilation: reality.timeDilation,
    rift: reality.riftIntensity,
    glitch: reality.glitchIntensity,
    cloneCount: reality.cloneCount,
    invisibility: reality.invisibilityEnabled,
    intangibility: reality.intangibilityEnabled,
    transcendent: reality.transcendentEnabled,
    conversations: chat.conversations.length,
    activeConversation: chat.activeId,
    messages: chat.messages.length,
    sidebarOpen: ui.sidebarOpen,
    theme: ui.theme,
  }

  return (
    <div className="fixed left-4 top-4 z-50 max-w-xs rounded-xl border border-white/10 bg-black/80 p-3 font-mono text-[10px] text-white/80 backdrop-blur-xl">
      <div className="mb-2 border-b border-white/10 pb-1 text-xs font-bold text-white">META-REALITY DEBUG</div>
      <pre className="whitespace-pre-wrap">{JSON.stringify(state, null, 2)}</pre>
      <div className="mt-2 flex gap-2">
        <button
          onClick={() => reality.reset()}
          className="rounded border border-white/20 bg-white/10 px-2 py-1 text-[10px] text-white hover:bg-white/20"
        >
          Reset Reality
        </button>
        <button
          onClick={() => reality.pushMultiverseSnapshot(state)}
          className="rounded border border-white/20 bg-white/10 px-2 py-1 text-[10px] text-white hover:bg-white/20"
        >
          Save Snapshot
        </button>
      </div>
    </div>
  )
}
