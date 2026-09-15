'use client';

import { SettingsNav } from '@/components/settings/settings-nav';
import { User, Palette, CreditCard, Key } from 'lucide-react';

const settingsItems = [
  { title: 'Profile', href: '/settings/profile', icon: User },
  { title: 'Appearance', href: '/settings/appearance', icon: Palette },
  { title: 'Billing', href: '/settings/billing', icon: CreditCard },
  { title: 'API Keys', href: '/settings/api-keys', icon: Key },
];

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Manage your account settings and preferences.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
        <aside className="hidden lg:block">
          <SettingsNav items={settingsItems} />
        </aside>
        <div className="lg:hidden">
          <SettingsNav items={settingsItems} />
        </div>
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="rounded-full bg-muted p-3">
              <User className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="mt-4 text-lg font-medium">Select a settings section</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Choose an option from the sidebar to manage your settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
