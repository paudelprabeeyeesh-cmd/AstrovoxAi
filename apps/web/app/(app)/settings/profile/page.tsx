'use client';

import { ProfileForm } from '@/components/settings/profile-form';

export default function ProfileSettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Profile</h1>
        <p className="text-muted-foreground">Manage your public profile information.</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        <ProfileForm
          initialData={{ name: 'User', email: 'user@astrovox.ai' }}
          avatarUrl="/avatars/user.jpg"
          onSave={async (data) => {
            console.log('Saving profile:', data);
          }}
        />
      </div>
    </div>
  );
}
