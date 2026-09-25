import { useState } from 'react'
import MultiverseDashboard from './MultiverseDashboard'
import TimelineVisualizer from './TimelineVisualizer'
import ForkVisualizer from './ForkVisualizer'
import ScenarioEngine from './ScenarioEngine'
import ParallelAssistant from './ParallelAssistant'
import MetaDebugTools from './MetaDebugTools'
import RealityEditor from './RealityEditor'
import TimeSpaceContinuum from './TimeSpaceContinuum'
import UniversalConstructor from './UniversalConstructor'
import InfiniteRecursion from './InfiniteRecursion'
import DimensionalPortal from './DimensionalPortal'

export default function MultiversePanel() {
  const [selectedTimelineId, setSelectedTimelineId] = useState(null)
  const [selectedUniverseId, setSelectedUniverseId] = useState(null)
  const [view, setView] = useState('dashboard')

  if (view === 'visualizer' && selectedUniverseId) {
    return (
      <TimelineVisualizer
        universeId={selectedUniverseId}
        onBack={() => { setSelectedUniverseId(null); setView('dashboard') }}
      />
    )
  }

  return (
    <div style={{ display: 'flex', height: '100%', gap: '16px' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto' }}>
        <MultiverseDashboard onSelectTimeline={setSelectedTimelineId} onSelectUniverse={setSelectedUniverseId} />
      </div>
      <div style={{ width: '360px', display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto' }}>
        {selectedTimelineId && (
          <ForkVisualizer timelineId={selectedTimelineId} onSelectUniverse={setSelectedUniverseId} />
        )}
        {selectedUniverseId && (
          <>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={() => setView('visualizer')} style={{ flex: 1, padding: '6px 12px', backgroundColor: 'rgba(6,182,212,0.15)', border: '1px solid #06b6d4', borderRadius: '6px', color: '#06b6d4', cursor: 'pointer', fontSize: '11px', fontFamily: 'inherit', fontWeight: '600' }}>
                View Timeline
              </button>
              <button onClick={() => setSelectedUniverseId(null)} style={{ padding: '6px 12px', backgroundColor: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', borderRadius: '6px', color: '#f87171', cursor: 'pointer', fontSize: '11px', fontFamily: 'inherit' }}>
                Clear
              </button>
            </div>
            <RealityEditor universeId={selectedUniverseId} />
            <TimeSpaceContinuum universeId={selectedUniverseId} />
            <ParallelAssistant universeId={selectedUniverseId} />
            <ScenarioEngine universeId={selectedUniverseId} />
            <InfiniteRecursion universeId={selectedUniverseId} />
            <DimensionalPortal universeId={selectedUniverseId} />
            <MetaDebugTools universeId={selectedUniverseId} />
          </>
        )}
        {!selectedTimelineId && (
          <div style={{ padding: '16px', backgroundColor: 'rgba(4,8,20,0.5)', border: '1px solid #1e293b', borderRadius: '8px', color: '#475569', fontSize: '11px', textAlign: 'center' }}>
            Select a timeline to unlock forks, parallel variants, scenarios, and meta-debug tools.
          </div>
        )}
      </div>
    </div>
  )
}
