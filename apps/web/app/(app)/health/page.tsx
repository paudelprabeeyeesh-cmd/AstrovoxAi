'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Activity, TrendingUp, TrendingDown, AlertCircle, CheckCircle2 } from 'lucide-react';
import { api } from '@/lib/api';
import { CustomerHealth } from '@/lib/api';

export default function HealthPage() {
  const [health, setHealth] = useState<CustomerHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ health: CustomerHealth }>('/cx/health');
      setHealth(data.health);
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  const recalculate = async () => {
    setCalculating(true);
    try {
      await loadHealth();
    } finally {
      setCalculating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!health) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Unable to load health score.</p>
      </div>
    );
  }

  const score = health.score;
  const healthColor = score >= 80 ? 'text-green-500' : score >= 50 ? 'text-yellow-500' : 'text-red-500';
  const healthLabel = score >= 80 ? 'Excellent' : score >= 50 ? 'Good' : 'Needs Attention';
  const healthIcon = score >= 80 ? CheckCircle2 : score >= 50 ? AlertCircle : TrendingDown;

  const factors = Object.entries(health.factors || {}).map(([key, value]) => ({
    name: key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
    value: value as number,
  }));

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Customer Health</h1>
        <p className="text-muted-foreground">Monitor your account health and engagement metrics.</p>
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-full bg-muted ${healthColor}`}>
              <Activity className="h-8 w-8" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Health Score</p>
              <p className={`text-4xl font-bold ${healthColor}`}>{Math.round(score)}</p>
              <p className={`text-sm font-medium ${healthColor}`}>{healthLabel}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={recalculate} disabled={calculating}>
            {calculating ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <TrendingUp className="h-4 w-4 mr-2" />}
            Recalculate
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-4">
          Last calculated: {new Date(health.last_calculated).toLocaleString()}
        </p>
      </Card>

      <Card className="p-6">
        <h3 className="font-semibold mb-4">Health Factors</h3>
        <div className="space-y-3">
          {factors.map((factor) => (
            <div key={factor.name} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{factor.name}</span>
                <span className="font-medium">{(factor.value * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    factor.value >= 0.8 ? 'bg-green-500' : factor.value >= 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${factor.value * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
