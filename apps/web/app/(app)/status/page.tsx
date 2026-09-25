'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Server, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';
import { StatusIncident, StatusSummary } from '@/lib/api';

const SERVICES = ['API', 'Web App', 'Chat', 'Database', 'AI Models'];

export default function StatusPage() {
  const [summary, setSummary] = useState<StatusSummary | null>(null);
  const [incidents, setIncidents] = useState<StatusIncident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    setLoading(true);
    try {
      const [summaryData, incidentsData] = await Promise.all([
        api.get<{ summary: StatusSummary }>('/support/status'),
        api.get<{ incidents: StatusIncident[] }>('/support/incidents'),
      ]);
      setSummary(summaryData.summary);
      setIncidents(incidentsData.incidents || []);
    } catch {
      setSummary(null);
      setIncidents([]);
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

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Status</h1>
        <p className="text-muted-foreground">Real-time status of AstrovoxAi services.</p>
      </div>

      <Card className="p-6">
        <div className="flex items-center gap-3 mb-4">
          {summary?.status === 'operational' ? (
            <CheckCircle2 className="h-6 w-6 text-green-500" />
          ) : (
            <AlertTriangle className="h-6 w-6 text-yellow-500" />
          )}
          <div>
            <h2 className="text-lg font-semibold capitalize">{summary?.status || 'Unknown'}</h2>
            <p className="text-sm text-muted-foreground">
              {summary?.active_incidents || 0} active incident{summary?.active_incidents !== 1 ? 's' : ''}
            </p>
          </div>
        </div>

        <div className="grid gap-3">
          {SERVICES.map((service) => (
            <div key={service} className="flex items-center justify-between p-3 rounded-md bg-muted/30">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{service}</span>
              </div>
              <Badge variant={summary?.status === 'operational' ? 'default' : 'secondary'}>
                {summary?.status === 'operational' ? 'Operational' : 'Degraded'}
              </Badge>
            </div>
          ))}
        </div>
      </Card>

      {incidents.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Incidents</h3>
          <div className="space-y-4">
            {incidents.map((incident) => (
              <div key={incident.id} className="border-b last:border-0 pb-4 last:pb-0">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium text-sm">{incident.title}</h4>
                    <p className="text-xs text-muted-foreground mt-1">{incident.description}</p>
                  </div>
                  <Badge variant={incident.status === 'resolved' ? 'default' : 'destructive'}>{incident.status}</Badge>
                </div>
                {incident.affected_services.length > 0 && (
                  <div className="flex gap-1 mt-2">
                    {incident.affected_services.map((svc) => (
                      <Badge key={svc} variant="secondary" className="text-xs">{svc}</Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
