import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

interface SettingsState {
  theme: string
  codeTheme: string
  voiceSpeed: number
  autoPlayVoice: boolean
  fontSize: 'small' | 'medium' | 'large'
  compactMode: boolean
  sendOnEnter: boolean
  showTimestamps: boolean
  showModelBadges: boolean
  soundEnabled: boolean
  updateSettings: (settings: Partial<SettingsState>) => void
}

export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set) => ({
        theme: 'system',
        codeTheme: 'github-dark',
        voiceSpeed: 1,
        autoPlayVoice: false,
        fontSize: 'medium',
        compactMode: false,
        sendOnEnter: true,
        showTimestamps: true,
        showModelBadges: true,
        soundEnabled: true,
        updateSettings: (newSettings) =>
          set((state) => ({ ...state, ...newSettings })),
      }),
      {
        name: 'settings-storage',
      }
    )
  )
)
