'use client'

import { useRealityStore } from '@/lib/store/reality-store'
import { GravityPanel } from './gravity-panels'
import { DimensionalRift } from './dimensional-rifts'
import { RealityGlitch } from './reality-glitches'
import { PhysicsDefyingInteraction } from './physics-defying'

export function RealityToolbar() {
  const {
    gravityEnabled,
    riftIntensity,
    glitchIntensity,
    setGravityEnabled,
    setRiftIntensity,
    setGlitchIntensity,
  } = useRealityStore()

  return (
    <GravityPanel className="fixed bottom-4 right-4 z-50">
      <DimensionalRift className="rounded-2xl border border-white/10 bg-black/60 p-3 backdrop-blur-xl">
        <div className="flex items-center gap-2 text-xs text-white/80">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={gravityEnabled}
              onChange={(e) => setGravityEnabled(e.target.checked)}
              className="h-3 w-3"
            />
            <RealityGlitch intensity={0.3}>Gravity</RealityGlitch>
          </label>
          <label className="flex items-center gap-1">
            <span>Rift</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={riftIntensity}
              onChange={(e) => setRiftIntensity(Number(e.target.value))}
              className="h-1 w-16"
            />
          </label>
          <label className="flex items-center gap-1">
            <span>Glitch</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={glitchIntensity}
              onChange={(e) => setGlitchIntensity(Number(e.target.value))}
              className="h-1 w-16"
            />
          </label>
        </div>
        <PhysicsDefyingInteraction className="mt-2">
          <div className="text-[10px] text-white/50">Physics override active</div>
        </PhysicsDefyingInteraction>
      </DimensionalRift>
    </GravityPanel>
  )
}
