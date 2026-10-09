'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Braces, Palette, Volume2 } from 'lucide-react'
import { useSettingsStore } from '@/lib/store/settings-store'

const CODE_THEMES = [
  { id: 'github-dark', name: 'GitHub Dark' },
  { id: 'github-light', name: 'GitHub Light' },
  { id: 'dracula', name: 'Dracula' },
  { id: 'monokai', name: 'Monokai' },
  { id: 'nord', name: 'Nord' },
  { id: 'solarized-dark', name: 'Solarized Dark' },
  { id: 'solarized-light', name: 'Solarized Light' },
]

const UI_THEMES = [
  { id: 'light', name: 'Light' },
  { id: 'dark', name: 'Dark' },
  { id: 'system', name: 'System' },
]

export function ThemePicker() {
  const { settings, updateSettings } = useSettingsStore()
  const [codeTheme, setCodeTheme] = useState(settings.codeTheme || 'github-dark')

  const handleCodeThemeChange = (theme: string) => {
    setCodeTheme(theme)
    updateSettings({ codeTheme: theme })
  }

  return (
    <div className="space-y-6">
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <Palette className="h-4 w-4" />
          <h3 className="text-sm font-medium">UI Theme</h3>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {UI_THEMES.map((theme) => (
            <button
              key={theme.id}
              onClick={() => updateSettings({ theme: theme.id })}
              className={`flex flex-col items-center justify-center rounded-lg border-2 p-3 text-center transition-colors ${
                (settings.theme || 'system') === theme.id
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:bg-muted'
              }`}
            >
              <span className="text-sm font-medium">{theme.name}</span>
            </button>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <Braces className="h-4 w-4" />
          <h3 className="text-sm font-medium">Code Syntax Theme</h3>
        </div>
        <Select value={codeTheme} onValueChange={handleCodeThemeChange}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CODE_THEMES.map((theme) => (
              <SelectItem key={theme.id} value={theme.id}>
                {theme.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Card>

      <Card className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <Volume2 className="h-4 w-4" />
          <h3 className="text-sm font-medium">Voice Output</h3>
        </div>
        <div className="space-y-3">
          <div className="space-y-2">
            <Label>Voice Speed</Label>
            <Slider
              value={[settings.voiceSpeed || 1]}
              onValueChange={(v) => updateSettings({ voiceSpeed: v[0] })}
              min={0.5}
              max={2}
              step={0.1}
            />
            <span className="text-xs text-muted-foreground">
              {(settings.voiceSpeed || 1).toFixed(1)}x
            </span>
          </div>
          <div className="flex items-center justify-between">
            <Label>Auto-play responses</Label>
            <input
              type="checkbox"
              checked={settings.autoPlayVoice || false}
              onChange={(e) => updateSettings({ autoPlayVoice: e.target.checked })}
              className="rounded"
            />
          </div>
        </div>
      </Card>
    </div>
  )
}
