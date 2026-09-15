'use client';

import { BillingPanel } from '@/components/settings/billing-panel';

const plan = {
  name: 'Pro',
  price: 29,
  interval: 'month' as const,
  currentUsage: 45200,
  limit: 100000,
  features: ['Unlimited conversations', 'Priority support', 'Advanced analytics', 'Custom integrations'],
};

const invoices = [
  { id: 'INV-001', date: new Date('2026-08-15'), amount: 29.00, status: 'paid' as const },
  { id: 'INV-002', date: new Date('2026-07-15'), amount: 29.00, status: 'paid' as const },
  { id: 'INV-003', date: new Date('2026-06-15'), amount: 29.00, status: 'paid' as const },
];

export default function BillingSettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
        <p className="text-muted-foreground">Manage your subscription and billing information.</p>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        <BillingPanel
          plan={plan}
          invoices={invoices}
          onUpgrade={() => console.log('Upgrade clicked')}
          onManageSubscription={() => console.log('Manage subscription clicked')}
          onDownloadInvoice={(id) => console.log('Download invoice:', id)}
        />
      </div>
    </div>
  );
}
