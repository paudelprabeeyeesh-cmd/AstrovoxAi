'use client';

import { useTheme } from 'next-themes';
import { Monitor, Moon, Sun } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';

const themes = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
] as const;

type ThemeValue = typeof themes[number]['value'];

interface ThemePickerProps {
  value?: ThemeValue;
  onValueChange?: (value: ThemeValue) => void;
}

export function ThemePicker({ value, onValueChange }: ThemePickerProps) {
  const { theme, setTheme } = useTheme();
  const selectedTheme = value || theme || 'system';

  const handleChange = (newValue: ThemeValue) => {
    onValueChange?.(newValue);
    setTheme(newValue);
  };

  const isSelected = (themeValue: ThemeValue) => selectedTheme === themeValue;
  const labelClass = (themeValue: ThemeValue) =>
    'flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 p-4 transition-colors ' +
    (isSelected(themeValue) ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted');

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-medium">Appearance</h3>
        <p className="text-sm text-muted-foreground">
          Customize the look and feel of the application
        </p>
      </div>
      <RadioGroup
        value={selectedTheme}
        onValueChange={(v) => handleChange(v as ThemeValue)}
        className="grid grid-cols-3 gap-4"
      >
        {themes.map((theme) => {
          const Icon = theme.icon;
          const id = 'theme-' + theme.value;
          return (
            <div key={theme.value}>
              <RadioGroupItem value={theme.value} id={id} className="sr-only" />
              <Label htmlFor={id} className={labelClass(theme.value)}>
                <Icon className="mb-2 h-6 w-6" />
                <span className="text-sm font-medium">{theme.label}</span>
              </Label>
            </div>
          );
        })}
      </RadioGroup>
      <p className="text-sm text-muted-foreground">
        {selectedTheme === 'system' && 'Follows your system preference'}
        {selectedTheme === 'light' && 'Light mode enabled'}
        {selectedTheme === 'dark' && 'Dark mode enabled'}
      </p>
    </div>
  );
}