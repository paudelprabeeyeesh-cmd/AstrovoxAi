'use client'

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

export type RealityMode = 'normal' | 'gravity' | 'timeDilation' | 'wormhole' | 'teleport' | 'clone' | 'invisible' | 'intangible' | 'warp' | 'sandbox' | 'meta' | 'rift' | 'glitch' | 'multiverse' | 'transcendent'

interface RealityState {
  mode: RealityMode
  gravityEnabled: boolean
  timeDilation: number
  riftIntensity: number
  glitchIntensity: number
  cloneCount: number
  invisibilityEnabled: boolean
  intangibilityEnabled: boolean
  transcendentEnabled: boolean
  multiverseSnapshots: unknown[]
  setMode: (mode: RealityMode) => void
  setGravityEnabled: (enabled: boolean) => void
  setTimeDilation: (dilation: number) => void
  setRiftIntensity: (intensity: number) => void
  setGlitchIntensity: (intensity: number) => void
  setCloneCount: (count: number) => void
  setInvisibilityEnabled: (enabled: boolean) => void
  setIntangibilityEnabled: (enabled: boolean) => void
  setTranscendentEnabled: (enabled: boolean) => void
  pushMultiverseSnapshot: (snapshot: unknown) => void
  restoreMultiverseSnapshot: (index: number) => void
  reset: () => void
}

const initialState = {
  mode: 'normal',
  gravityEnabled: false,
  timeDilation: 1,
  riftIntensity: 0,
  glitchIntensity: 0,
  cloneCount: 1,
  invisibilityEnabled: false,
  intangibilityEnabled: false,
  transcendentEnabled: false,
  multiverseSnapshots: [] as unknown[],
}

export const useRealityStore = create<RealityState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        setMode: (mode) => set({ mode }),
        setGravityEnabled: (gravityEnabled) => set({ gravityEnabled }),
        setTimeDilation: (timeDilation) => set({ timeDilation }),
        setRiftIntensity: (riftIntensity) => set({ riftIntensity }),
        setGlitchIntensity: (glitchIntensity) => set({ glitchIntensity }),
        setCloneCount: (cloneCount) => set({ cloneCount }),
        setInvisibilityEnabled: (invisibilityEnabled) => set({ invisibilityEnabled }),
        setIntangibilityEnabled: (intangibilityEnabled) => set({ intangibilityEnabled }),
        setTranscendentEnabled: (transcendentEnabled) => set({ transcendentEnabled }),
        pushMultiverseSnapshot: (snapshot) =>
          set((state) => ({
            multiverseSnapshots: [...state.multiverseSnapshots, snapshot],
          })),
        restoreMultiverseSnapshot: (index) => {
          const snapshots = get().multiverseSnapshots
          if (index >= 0 && index < snapshots.length) {
            set({ multiverseSnapshots: snapshots.slice(0, index + 1) })
          }
        },
        reset: () => set(initialState),
      }),
      { name: 'reality-storage' }
    ),
    { name: 'RealityStore' }
  )
)
