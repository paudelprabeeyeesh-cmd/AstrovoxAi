'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Activity, Ticket, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { CustomerPortal } from '@/lib/api';
import Link from 'next/link';

export default function CustomerPortalPage() {
  const [portal, setPortal] = useState<CustomerPortal | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPortal();
  }, []);

  const loadPortal = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ portal: CustomerPortal }>('/support/portal');
      setPortal(data.portal);
    } catch {
      setPortal(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!portal) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Unable to load portal.</p>
      </div>
    );
  }

  const healthScore = portal.health?.score || 0;
  const healthColor = healthScore >= 80 ? 'text-green-500' : healthScore >= 50 ? 'text-yellow-500' : 'text-red-500';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Customer Portal</h1>
        <p className="text-muted-foreground">Manage your support experience and account health.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <Activity className={`h-5 w-5 ${healthColor}`} />
            <div>
              <p className="text-sm text-muted-foreground">Health Score</p>
              <p className={`text-2xl font-bold ${healthColor}`}>{Math.round(healthScore)}</p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {healthScore >= 80 ? 'Excellent' : healthScore >= 50 ? 'Good' : 'Needs Attention'}
          </p>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-3">
            <Ticket className="h-5 w-5 text-primary" />
            <div>
              <p className="text-sm text-muted-foreground">Open Tickets</p>
              <p className="text-2xl font-bold">{portal.tickets?.filter((t: any) => t.status === 'open').length || 0}</p>
            </div>
          </div>
          <Link href="/support">
            <Button variant="ghost" size="sm" className="mt-2 p-0 h-auto text-xs">View all tickets</Button>
          </Link>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-3">
            {portal.onboarding?.completed ? (
              <CheckCircle2 className="h-5 w-5 text-green-500" />
            ) : (
              <AlertCircle className="h-5 w-5 text-yellow-500" />
            )}
            <div>
              <p className="text-sm text-muted-foreground">Onboarding</p>
              <p className="text-2xl font-bold">{portal.onboarding?.completed ? 'Complete' : 'In Progress'}</p>
            </div>
          </div>
          {!portal.onboarding?.completed && (
            <Link href="/onboarding">
              <Button variant="ghost" size="sm" className="mt-2 p-0 h-auto text-xs">Continue onboarding</Button>
            </Link>
          )}
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="font-semibold mb-4">Recent Tickets</h3>
        {portal.tickets?.length === 0 ? (
          <p className="text-sm text-muted-foreground">No tickets yet.</p>
        ) : (
          <div className="space-y-2">
            {portal.tickets?.slice(0, 5).map((ticket: any) => (
              <Link key={ticket.id} href={`/support`} className="block">
                <div className="flex items-center justify-between p-3 rounded-md bg-muted/30 hover:bg-accent transition-colors">
                  <div>
                    <p className="font-medium text-sm">{ticket.subject}</p>
                    <p className="text-xs text-muted-foreground">{ticket.category}</p>
                  </div>
                  <Badge variant={ticket.status === 'open' ? 'default' : 'secondary'}>{ticket.status}</Badge>
                </div>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
