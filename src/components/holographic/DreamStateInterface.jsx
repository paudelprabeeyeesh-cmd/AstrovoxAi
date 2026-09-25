import { useDreamState } from '../../hooks/holographic/useDreamState'
import { HOLOGRAPHIC_COLORS, HOLOGRAPHIC_LAYOUTS } from '../../utils/holographic/HolographicConfig'

export function DreamStateInterface({ className = '', style = {} }) {
  const {
    isDreaming,
    dreamPhase,
    dreamClarity,
    lucidityLevel,
    dreamScenes,
    dreamNarrative,
    isLucidAssistantActive,
    enterDreamState,
    exitDreamState,
    activateLucidAssistant,
    deactivateLucidAssistant,
    stabilizeLucidity,
    performRealityCheck,
    setDreamPhase
  } = useDreamState()

  const phaseOptions = ['drowsy', 'light_sleep', 'rem', 'deep_sleep', 'lucid']

  return (
    <div
      className={className}
      style={{
        ...HOLOGRAPHIC_LAYOUTS.hologramCard,
        ...style
      }}
    >
      <div style={{
        padding: '16px',
        borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h3 style={{
            margin: '0 0 4px 0',
            color: HOLOGRAPHIC_COLORS.accent,
            fontSize: '16px',
            fontWeight: 600
          }}>
            Dream State Interface
          </h3>
          <p style={{ margin: 0, color: 'var(--astrovox-text-muted)', fontSize: '12px' }}>
            Phase: {dreamPhase} | Clarity: {(dreamClarity * 100).toFixed(0)}% | Lucidity: {(lucidityLevel * 100).toFixed(0)}%
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {!isDreaming ? (
            <button
              onClick={() => enterDreamState(dreamPhase)}
              style={{
                padding: '8px 16px',
                background: `linear-gradient(135deg, ${HOLOGRAPHIC_COLORS.primary}30, ${HOLOGRAPHIC_COLORS.secondary}30)`,
                border: `1px solid ${HOLOGRAPHIC_COLORS.primary}60`,
                borderRadius: '6px',
                color: HOLOGRAPHIC_COLORS.accent,
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              Enter Dream
            </button>
          ) : (
            <button
              onClick={exitDreamState}
              style={{
                padding: '8px 16px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                borderRadius: '6px',
                color: HOLOGRAPHIC_COLORS.error,
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              Exit Dream
            </button>
          )}
        </div>
      </div>

      <div style={{ padding: '16px' }}>
        {isDreaming && (
          <div style={{ marginBottom: '16px' }}>
            <label style={{
              color: HOLOGRAPHIC_COLORS.accent,
              fontSize: '12px',
              marginBottom: '8px',
              display: 'block'
            }}>
              Dream Phase
            </label>
            <select
              value={dreamPhase}
              onChange={(e) => setDreamPhase(e.target.value)}
              style={{
                ...HOLOGRAPHIC_LAYOUTS.hologramInput,
                padding: '8px 12px',
                fontSize: '12px',
                width: '100%'
              }}
            >
              {phaseOptions.map(phase => (
                <option key={phase} value={phase} style={{ background: '#02040a' }}>
                  {phase.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        )}

        <div style={{
          display: 'flex',
          gap: '12px',
          marginBottom: '16px',
          flexWrap: 'wrap'
        }}>
          <div style={{
            flex: 1,
            minWidth: '100px',
            padding: '12px',
            background: 'rgba(6, 182, 212, 0.05)',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <div style={{
              color: HOLOGRAPHIC_COLORS.consciousness,
              fontSize: '20px',
              fontWeight: 'bold'
            }}>
              {(dreamClarity * 100).toFixed(0)}%
            </div>
            <div style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
              Clarity
            </div>
          </div>
          <div style={{
            flex: 1,
            minWidth: '100px',
            padding: '12px',
            background: 'rgba(244, 114, 182, 0.05)',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <div style={{
              color: HOLOGRAPHIC_COLORS.secondary,
              fontSize: '20px',
              fontWeight: 'bold'
            }}>
              {(lucidityLevel * 100).toFixed(0)}%
            </div>
            <div style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
              Lucidity
            </div>
          </div>
          <div style={{
            flex: 1,
            minWidth: '100px',
            padding: '12px',
            background: 'rgba(167, 139, 250, 0.05)',
            borderRadius: '8px',
            textAlign: 'center'
          }}>
            <div style={{
              color: HOLOGRAPHIC_COLORS.quantum,
              fontSize: '20px',
              fontWeight: 'bold'
            }}>
              {dreamScenes.length}
            </div>
            <div style={{ color: 'var(--astrovox-text-muted)', fontSize: '11px' }}>
              Scenes
            </div>
          </div>
        </div>

        {isDreaming && (
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <button
              onClick={isLucidAssistantActive ? deactivateLucidAssistant : activateLucidAssistant}
              style={{
                padding: '6px 12px',
                background: isLucidAssistantActive ? 'rgba(167, 139, 250, 0.2)' : 'rgba(6, 182, 212, 0.1)',
                border: `1px solid ${isLucidAssistantActive ? HOLOGRAPHIC_COLORS.quantum : HOLOGRAPHIC_COLORS.primary}40`,
                borderRadius: '6px',
                color: isLucidAssistantActive ? HOLOGRAPHIC_COLORS.quantum : HOLOGRAPHIC_COLORS.accent,
                fontSize: '11px',
                cursor: 'pointer'
              }}
            >
              {isLucidAssistantActive ? 'Deactivate Assistant' : 'Lucid Assistant'}
            </button>
            {isLucidAssistantActive && (
              <button
                onClick={stabilizeLucidity}
                style={{
                  padding: '6px 12px',
                  background: 'rgba(52, 211, 153, 0.1)',
                  border: '1px solid rgba(52, 211, 153, 0.4)',
                  borderRadius: '6px',
                  color: HOLOGRAPHIC_COLORS.success,
                  fontSize: '11px',
                  cursor: 'pointer'
                }}
              >
                Stabilize
              </button>
            )}
            <button
              onClick={performRealityCheck}
              style={{
                padding: '6px 12px',
                background: 'rgba(251, 191, 36, 0.1)',
                border: '1px solid rgba(251, 191, 36, 0.4)',
                borderRadius: '6px',
                color: HOLOGRAPHIC_COLORS.warning,
                fontSize: '11px',
                cursor: 'pointer'
              }}
            >
              Reality Check
            </button>
          </div>
        )}

        {dreamNarrative && (
          <div style={{
            padding: '12px',
            background: 'rgba(6, 182, 212, 0.05)',
            borderRadius: '8px',
            marginBottom: '16px',
            border: '1px solid rgba(6, 182, 212, 0.2)'
          }}>
            <p style={{
              margin: 0,
              color: HOLOGRAPHIC_COLORS.accent,
              fontSize: '13px',
              fontStyle: 'italic'
            }}>
              {dreamNarrative}
            </p>
          </div>
        )}

        {dreamScenes.length > 0 && (
          <div>
            <h4 style={{ color: HOLOGRAPHIC_COLORS.accent, margin: '0 0 8px 0', fontSize: '13px' }}>
              Dream Scenes
            </h4>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              maxHeight: '200px',
              overflowY: 'auto'
            }}>
              {dreamScenes.slice(-10).map((scene, index) => (
                <div
                  key={scene.id || index}
                  style={{
                    padding: '8px 12px',
                    background: 'rgba(167, 139, 250, 0.05)',
                    borderRadius: '6px',
                    border: '1px solid rgba(167, 139, 250, 0.2)',
                    fontSize: '12px'
                  }}
                >
                  <div style={{ color: HOLOGRAPHIC_COLORS.dream, marginBottom: '4px' }}>
                    {scene.type?.replace('_', ' ') || 'unknown'}
                  </div>
                  <div style={{ color: 'var(--astrovox-text-muted)' }}>
                    Opacity: {((scene.opacity || 0) * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
