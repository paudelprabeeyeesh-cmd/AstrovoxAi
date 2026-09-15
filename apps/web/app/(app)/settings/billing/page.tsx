'use client';

import { useState, useEffect } from 'react';
import { BillingPanel } from '@/components/settings/billing-panel';
import { api } from '@/lib/api';

interface PlanInfo {
  plan: string;
  status: string;
  currentUsage: number;
  limit: number;
}

interface Invoice {
  id: string;
  date: string;
  amount: number;
  status: string;
}

export default function BillingSettingsPage() {
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadBillingData() {
      setLoading(true);
      setError(null);
      try {
        const [planData, invoicesData] = await Promise.all([
          api.get<PlanInfo>('/billing/current'),
          api.get<Invoice[]>('/billing/invoices'),
        ]);
        setPlan(planData);
        setInvoices(invoicesData);
      } catch {
        setError('Failed to load billing data');
      } finally {
        setLoading(false);
      }
    }
    loadBillingData();
  }, []);

  const planDisplay = plan ? {
    name: plan.plan.charAt(0).toUpperCase() + plan.plan.slice(1),
    price: plan.plan === 'pro' ? 29 : plan.plan === 'team' ? 79 : 0,
    interval: 'month' as const,
    currentUsage: plan.currentUsage,
    limit: plan.limit,
    features: plan.plan === 'team'
      ? ['Unlimited conversations', 'Priority support', 'Advanced analytics', 'Custom integrations', 'Team management']
      : plan.plan === 'pro'
      ? ['Unlimited conversations', 'Priority support', 'Advanced analytics', 'Custom integrations']
      : ['Basic conversations', 'Standard support'],
  } : {
    name: 'Free',
    price: 0,
    interval: 'month' as const,
    currentUsage: 0,
    limit: 100,
    features: ['Basic conversations', 'Standard support'],
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
        <p className="text-muted-foreground">Manage your subscription and billing information.</p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
          <BillingPanel
            plan={planDisplay}
            invoices={invoices.map(inv => ({
              id: inv.id,
              date: new Date(inv.date),
              amount: inv.amount,
              status: inv.status as 'paid' | 'pending' | 'failed',
            }))}
            onUpgrade={() => { window.location.href = '/api/billing/checkout'; }}
            onDowngrade={() => { window.location.href = '/api/billing/cancel'; }}
            onManageSubscription={() => { window.location.href = '/api/billing/portal'; }}
            onDownloadInvoice={async (id) => {
              const res = await fetch(`/api/billing/invoices/${id}/download`);
              if (!res.ok) throw new Error('Download failed');
              const blob = await res.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `invoice-${id}.pdf`;
              a.click();
            }}
          />
        </div>
      )}
    </div>
  );
}
