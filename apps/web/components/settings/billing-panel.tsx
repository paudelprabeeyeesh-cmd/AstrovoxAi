'use client';

import { useState } from 'react';
import { FileText, Download, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface Invoice {
  id: string;
  date: Date;
  amount: number;
  status: 'paid' | 'pending' | 'failed';
  downloadUrl?: string;
}

interface PlanInfo {
  name: string;
  price: number;
  interval: 'month' | 'year';
  currentUsage: number;
  limit: number;
  features: string[];
}

interface BillingPanelProps {
  plan?: PlanInfo;
  invoices?: Invoice[];
  onUpgrade?: () => void;
  onManageSubscription?: () => void;
  onDownloadInvoice?: (invoiceId: string) => Promise<void>;
}

const statusStyles = {
  paid: 'bg-green-500/10 text-green-600 dark:text-green-400',
  pending: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400',
  failed: 'bg-red-500/10 text-red-600 dark:text-red-400',
};

export function BillingPanel({
  plan,
  invoices = [],
  onUpgrade,
  onManageSubscription,
  onDownloadInvoice,
}: BillingPanelProps) {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
    const usagePercentage = plan ? Math.min((plan.currentUsage / plan.limit) * 100, 100) : 0;

  const handleDownload = async (invoice: Invoice) => {
    setDownloadingId(invoice.id);
    try {
      await onDownloadInvoice?.(invoice.id);
    } finally {
      setDownloadingId(null);
    }
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">Billing & Plans</h3>
        <p className="text-sm text-muted-foreground">
          Manage your subscription and billing information
        </p>
      </div>

      {plan && (
        <Card className="p-6">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="text-xl font-bold">{plan.name} Plan</h4>
              <p className="mt-1 text-3xl font-bold">
                
                <span className="text-lg font-normal text-muted-foreground">
                  /{plan.interval === 'month' ? 'mo' : 'yr'}
                </span>
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={onManageSubscription}>
                Manage
              </Button>
              <Button onClick={onUpgrade}>Upgrade</Button>
            </div>
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Usage</span>
              <span className="font-medium">
                {plan.currentUsage.toLocaleString()} / {plan.limit.toLocaleString()}
              </span>
            </div>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: usagePercentage + '%' }}
              />
            </div>
          </div>

          <ul className="mt-6 grid grid-cols-2 gap-3">
            {plan.features.map((feature) => (
              <li key={feature} className="flex items-center gap-2 text-sm">
                <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                {feature}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div>
        <h4 className="text-md font-medium mb-4">Invoice History</h4>
        <div className="space-y-3">
          {invoices.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No invoices yet
            </p>
          ) : (
            invoices.map((invoice) => {
              const statusClass = statusStyles[invoice.status];
              return (
                <div
                  key={invoice.id}
                  className="flex items-center justify-between rounded-lg border border-border p-4"
                >
                  <div className="flex items-center gap-4">
                    <div className="rounded-md bg-muted p-2">
                      <FileText className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">Invoice #{invoice.id}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(invoice.date)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={'rounded-full px-2 py-1 text-xs font-medium ' + statusClass}>
                      {invoice.status}
                    </span>
                    <span className="text-sm font-medium">
                      
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownload(invoice)}
                      disabled={downloadingId === invoice.id}
                    >
                      {downloadingId === invoice.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
