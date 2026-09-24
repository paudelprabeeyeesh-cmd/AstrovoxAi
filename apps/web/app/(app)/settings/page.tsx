'use client';

import { useState } from 'react';
import { User, Key, Palette, Bell, Settings2, Loader2 } from 'lucide-react';
import { SettingsNav } from '@/components/settings/settings-nav';
import { ProfileForm } from '@/components/settings/profile-form';
import { ApiKeyManager } from '@/components/settings/api-key-manager';
import { ThemePicker } from '@/components/settings/theme-picker';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { ModelOption } from '@/components/chat/types';

const settingsItems = [
  { title: 'Profile', href: '/settings/profile', icon: User },
  { title: 'Appearance', href: '/settings/appearance', icon: Palette },
  { title: 'Billing', href: '/settings/billing', icon: Settings2 },
  { title: 'API Keys', href: '/settings/api-keys', icon: Key },
];

const models: ModelOption[] = [
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI' },
  { id: 'claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
  { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google' },
  { id: 'llama-3.1-70b', name: 'Llama 3.1 70B', provider: 'Meta' },
  { id: 'mistral-large', name: 'Mistral Large', provider: 'Mistral' },
];

export default function SettingsPage() {
  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  const [notifications, setNotifications] = useState({
    email: true,
    push: true,
    marketing: false,
    security: true,
    weeklyDigest: true,
  });
  const [isSavingNotifications, setIsSavingNotifications] = useState(false);

  const handleNotificationToggle = async (key: keyof typeof notifications) => {
    setIsSavingNotifications(true);
    setNotifications((prev) => ({ ...prev, [key]: !prev[key] }));
    await new Promise((resolve) => setTimeout(resolve, 600));
    setIsSavingNotifications(false);
  };

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

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <User className="h-5 w-5" />
                <CardTitle>Profile</CardTitle>
              </div>
              <CardDescription>Update your public profile information.</CardDescription>
            </CardHeader>
            <CardContent>
              <ProfileForm
                initialData={{ name: 'User', email: 'user@astrovox.ai' }}
                avatarUrl="/avatars/user.jpg"
                onSave={async (data) => {
                  console.log('Saving profile:', data);
                }}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Palette className="h-5 w-5" />
                <CardTitle>Theme</CardTitle>
              </div>
              <CardDescription>Customize the look and feel of the application.</CardDescription>
            </CardHeader>
            <CardContent>
              <ThemePicker />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
                <CardTitle>Model Preferences</CardTitle>
              </div>
              <CardDescription>Choose your default AI model for conversations.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Default Model</label>
                  <Select value={selectedModel} onValueChange={setSelectedModel}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a model" />
                    </SelectTrigger>
                    <SelectContent>
                      {models.map((model) => (
                        <SelectItem key={model.id} value={model.id}>
                          {model.name}
                          <span className="ml-2 text-xs text-muted-foreground">({model.provider})</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Response Style</label>
                  <div className="grid grid-cols-3 gap-3">
                    {(['Balanced', 'Precise', 'Creative'] as const).map((style) => (
                      <label
                        key={style}
                        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 p-3 text-center transition-colors ${
                          style === 'Balanced'
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:bg-muted'
                        }`}
                      >
                        <input
                          type="radio"
                          name="response-style"
                          value={style.toLowerCase()}
                          defaultChecked={style === 'Balanced'}
                          className="sr-only"
                        />
                        <span className="text-sm font-medium">{style}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                <CardTitle>Notifications</CardTitle>
              </div>
              <CardDescription>Manage how and when you receive notifications.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {(
                  [
                    { key: 'email', label: 'Email Notifications', description: 'Receive updates via email' },
                    { key: 'push', label: 'Push Notifications', description: 'Receive push notifications in your browser' },
                    { key: 'marketing', label: 'Marketing Emails', description: 'Receive product updates and offers' },
                    { key: 'security', label: 'Security Alerts', description: 'Get notified about account security events' },
                    { key: 'weeklyDigest', label: 'Weekly Digest', description: 'Receive a weekly summary of your activity' },
                  ] as const
                ).map(({ key, label, description }) => (
                  <div key={key} className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <label className="text-sm font-medium">{label}</label>
                      <p className="text-xs text-muted-foreground">{description}</p>
                    </div>
                    <Switch
                      checked={notifications[key]}
                      onCheckedChange={() => handleNotificationToggle(key)}
                      disabled={isSavingNotifications}
                    />
                  </div>
                ))}
                {isSavingNotifications && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving...
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                <CardTitle>API Keys</CardTitle>
              </div>
              <CardDescription>Manage API keys for programmatic access.</CardDescription>
            </CardHeader>
            <CardContent>
              <ApiKeyManager
                keys={[
                  {
                    id: '1',
                    name: 'Production Key',
                    key: 'sk-1234567890abcdef1234567890abcdef12345678',
                    createdAt: new Date('2024-01-15'),
                    lastUsed: new Date('2024-09-20'),
                  },
                ]}
                onCreateKey={async (name) => {
                  console.log('Creating key:', name);
                  return {
                    id: Date.now().toString(),
                    name,
                    key: 'sk-' + Math.random().toString(36).slice(2, 34),
                    createdAt: new Date(),
                  };
                }}
                onRevokeKey={async (id) => {
                  console.log('Revoking key:', id);
                }}
                onCreateDialogOpen={false}
                onOpenChange={() => {}}
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
