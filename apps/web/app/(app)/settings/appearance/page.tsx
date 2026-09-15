'use client';

import { ThemePicker } from '@/components/settings/theme-picker';

export default function AppearanceSettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Appearance</h1>
        <p className="text-muted-foreground">Customize the look and feel of the application.</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        <ThemePicker />
      </div>
    </div>
  );
}
