import { useMemo } from 'react'
import { useSettingsStore } from '@/lib/store/settings-store'

export function useSettings() {
  const preferences = useSettingsStore((state) => state.preferences)
  const setPreference = useSettingsStore((state) => state.setPreference)
  const resetPreferences = useSettingsStore((state) => state.resetPreferences)

  const fontSizeClass = useMemo(() => {
    switch (preferences.fontSize) {
      case 'small':
        return 'text-sm'
      case 'large':
        return 'text-lg'
      default:
        return 'text-base'
    }
  }, [preferences.fontSize])

  return {
    preferences,
    setPreference,
    resetPreferences,
    fontSizeClass,
  }
}
