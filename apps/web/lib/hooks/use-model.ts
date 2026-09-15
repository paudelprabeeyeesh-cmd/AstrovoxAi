import { useCallback } from 'react'
import { useSettingsStore } from '@/lib/store/settings-store'
import { MODELS } from '@/lib/constants'
import type { ModelId } from '@/lib/constants'

export function useModel() {
  const { modelId, setModelId } = useSettingsStore()

  const models = Object.values(MODELS)
  const activeModel = MODELS[modelId]

  const selectModel = useCallback(
    (id: ModelId) => {
      if (id in MODELS) {
        setModelId(id)
      }
    },
    [setModelId]
  )

  return {
    models,
    activeModel,
    modelId,
    selectModel,
  }
}
