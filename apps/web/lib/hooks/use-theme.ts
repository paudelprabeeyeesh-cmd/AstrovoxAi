import { useCallback, useEffect } from 'react'
import { useUIStore } from '@/lib/store/ui-store'
import { useSettingsStore } from '@/lib/store/settings-store'

export function useTheme() {
  const { theme: uiTheme, resolvedTheme, setTheme: setUITheme } = useUIStore()
  const { theme: settingsTheme, setTheme: setSettingsTheme } = useSettingsStore()

  useEffect(() => {
    const root = document.documentElement
    root.classList.remove('light', 'dark')

    const effective = resolvedTheme
    root.classList.add(effective)

    if (effective === 'dark') {
      root.style.colorScheme = 'dark'
    } else {
      root.style.colorScheme = 'light'
    }
  }, [resolvedTheme])

  const setTheme = useCallback(
    (newTheme: 'light' | 'dark' | 'system') => {
      setUITheme(newTheme)
      setSettingsTheme(newTheme)
    },
    [setUITheme, setSettingsTheme]
  )

  return {
    theme: settingsTheme,
    resolvedTheme,
    setTheme,
  }
}
