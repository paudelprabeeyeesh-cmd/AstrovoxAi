'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, BarChart3, TrendingUp, MessageSquare, Ticket } from 'lucide-react';
import { api } from '@/lib/api';
import { SupportAnalytic } from '@/lib/api';

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<SupportAnalytic[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('daily');

  useEffect(() => {
    loadAnalytics();
  }, [period]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ analytics: SupportAnalytic[] }>(`/cx/analytics?period=${period}`);
      setAnalytics(data.analytics || []);
    } catch {
      setAnalytics([]);
    } finally {
      setLoading(false);
    }
  };

  const metricGroups = analytics.reduce((acc, item) => {
    if (!acc[item.metric_name]) {
      acc[item.metric_name] = [];
    }
    acc[item.metric_name].push(item);
    return acc;
  }, {} as Record<string, SupportAnalytic[]>);

  const totalMetrics = Object.keys(metricGroups).length;
  const latestValues = Object.entries(metricGroups).map(([name, items]) => {
    const sorted = items.sort((a, b) => b.created_at - a.created_at);
    return { name, value: sorted[0]?.metric_value ?? 0 };
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Support Analytics</h1>
        <p className="text-muted-foreground">Track support performance and customer satisfaction metrics.</p>
      </div>

      <div className="flex gap-2">
        {['daily', 'weekly', 'monthly'].map((p) => (
          <Badge
            key={p}
            variant={period === p ? 'default' : 'secondary'}
            className="cursor-pointer capitalize"
            onClick={() => setPeriod(p)}
          >
            {p}
          </Badge>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-5 w-5 text-primary" />
            <div>
              <p className="text-sm text-muted-foreground">Total Metrics</p>
              <p className="text-2xl font-bold">{totalMetrics}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <TrendingUp className="h-5 w-5 text-green-500" />
            <div>
              <p className="text-sm text-muted-foreground">Data Points</p>
              <p className="text-2xl font-bold">{analytics.length}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <MessageSquare className="h-5 w-5 text-blue-500" />
            <div>
              <p className="text-sm text-muted-foreground">Avg. Metric Value</p>
              <p className="text-2xl font-bold">
                {latestValues.length > 0
                  ? (latestValues.reduce((sum, m) => sum + m.value, 0) / latestValues.length).toFixed(1)
                  : 0}
              </p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <Ticket className="h-5 w-5 text-orange-500" />
            <div>
              <p className="text-sm text-muted-foreground">Period</p>
              <p className="text-2xl font-bold capitalize">{period}</p>
            </div>
          </div>
        </Card>
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {latestValues.map((metric) => (
            <Card key={metric.name} className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium capitalize">{metric.name.replace(/_/g, ' ')}</p>
                  <p className="text-2xl font-bold">{metric.value.toFixed(1)}</p>
                </div>
                <Badge variant="secondary" className="capitalize">{period}</Badge>
              </div>
            </Card>
          ))}
        </div>
      )}

      {!loading && analytics.length > 0 && (
        <Card className="p-6">
          <h3 className="font-semibold mb-4">Recent Metrics</h3>
          <div className="space-y-2">
            {analytics.slice(0, 10).map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3 rounded-md bg-muted/30">
                <div>
                  <p className="font-medium text-sm capitalize">{item.metric_name.replace(/_/g, ' ')}</p>
                  <p className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</p>
                </div>
                <Badge variant="outline">{item.metric_value.toFixed(1)}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
