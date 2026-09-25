import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { ModelId } from '@/lib/constants'

interface SettingsState {
  preferences: {
    fontSize: 'small' | 'medium' | 'large'
    sendOnEnter: boolean
    showTimestamps: boolean
    autoScroll: boolean
    soundEnabled: boolean
  }
  theme: 'light' | 'dark' | 'system'
  modelId: ModelId
  setPreference: <K extends keyof SettingsState['preferences']>(
    key: K,
    value: SettingsState['preferences'][K]
  ) => void
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setModelId: (modelId: ModelId) => void
  resetPreferences: () => void
}

const defaultPreferences: SettingsState['preferences'] = {
  fontSize: 'medium',
  sendOnEnter: true,
  showTimestamps: true,
  autoScroll: true,
  soundEnabled: true,
}

export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set) => ({
        preferences: { ...defaultPreferences },
        theme: 'system',
        modelId: 'gpt-4o',

        setPreference: (key, value) =>
          set((state) => ({
            preferences: { ...state.preferences, [key]: value },
          })),

        setTheme: (theme) => set({ theme }),
        setModelId: (modelId) => set({ modelId }),
        resetPreferences: () => set({ preferences: { ...defaultPreferences } }),
      }),
      {
        name: 'settings-storage',
      }
    ),
    { name: 'SettingsStore' }
  )
)
