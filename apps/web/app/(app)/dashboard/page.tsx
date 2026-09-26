'use client';

import { useState, useEffect } from 'react';
import { StatCard } from '@/components/dashboard/stat-card';
import { UsageChart } from '@/components/dashboard/usage-chart';
import { CostTracker } from '@/components/dashboard/cost-tracker';
import { RecentActivity } from '@/components/dashboard/recent-activity';
import { MessageSquare, Zap, DollarSign, TrendingUp, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface DashboardOverview {
  usage: {
    total_requests: number;
    total_tokens: number;
    active_users: number;
    avg_latency: number;
    error_rate: number;
  };
  ai_usage: {
    total_requests: number;
    success_rate: number;
    avg_latency: number;
  };
  tokens: {
    total_tokens: number;
    total_cost: number;
  };
  costs: {
    total_cost: number;
    trend: string;
  };
  models: {
    model_count: number;
    best_by_latency: string | null;
    best_by_success: string | null;
  };
  users: {
    active_users: number;
    total_actions: number;
  };
}

interface TokenAnalytics {
  total_tokens: number;
  total_cost: number;
  avg_tokens_per_request: number;
  tokens_by_day: Record<string, number>;
}

interface CostAnalytics {
  total_api_cost: number;
  daily_costs: Record<string, number>;
  forecast_next_period: number;
}

interface RealtimeEvent {
  title: string;
  description: string;
  timestamp: number;
  type: 'chat' | 'api' | 'billing' | 'system';
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [tokenAnalytics, setTokenAnalytics] = useState<TokenAnalytics | null>(null);
  const [costAnalytics, setCostAnalytics] = useState<CostAnalytics | null>(null);
  const [realtime, setRealtime] = useState<{ events_today: number; cost_today: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, tokensRes, costsRes, realtimeRes] = await Promise.all([
        api.get<{ data: DashboardOverview }>('/analytics/overview?days=7'),
        api.get<{ data: TokenAnalytics }>('/analytics/tokens?days=7'),
        api.get<{ data: CostAnalytics }>('/analytics/costs?days=7'),
        api.get<{ data: { events_today: number; cost_today: number } }>('/analytics/realtime?days=1'),
      ])
      setOverview(overviewRes.data);
      setTokenAnalytics(tokensRes.data);
      setCostAnalytics(costsRes.data);
      setRealtime(realtimeRes.data);
    } catch {
      setError('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }

  const formatNumber = (value: number): string => {
    if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M'
    if (value >= 1_000) return (value / 1_000).toFixed(1) + 'K'
    return value.toString()
  }

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value)
  }

  const usageChartData = tokenAnalytics?.tokens_by_day
    ? Object.entries(tokenAnalytics.tokens_by_day).map(([date, tokens]) => ({
        date,
        tokens,
        cost: parseFloat(((tokens / 1000) * 0.001).toFixed(4)),
      }))
    : []

  const costChartData = costAnalytics?.daily_costs
    ? Object.entries(costAnalytics.daily_costs).map(([period, amount]) => ({
        period,
        amount: parseFloat(amount.toFixed(2)),
        budget: 20,
      }))
    : []

  const recentActivities: RealtimeEvent[] = realtime
    ? [
        {
          id: '1',
          title: 'API usage today',
          description: `${realtime.events_today} events processed today`,
          timestamp: Date.now(),
          type: 'api',
        },
        {
          id: '2',
          title: 'Cost today',
          description: `Spent ${formatCurrency(realtime.cost_today)} today`,
          timestamp: Date.now() - 1000 * 60 * 5,
          type: 'billing',
        },
      ]
    : []

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-6 text-center">
        <p className="text-sm text-destructive">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back! Here is your overview.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Conversations"
          value={formatNumber(overview?.users.total_actions ?? 0)}
          description={`${overview?.users.active_users ?? 0} active users`}
          icon={MessageSquare}
          trend={{ value: 12, label: 'vs last month' }}
        />
        <StatCard
          title="API Calls"
          value={formatNumber(overview?.ai_usage.total_requests ?? 0)}
          description={`${overview?.ai_usage.success_rate ?? 0}% success rate`}
          icon={Zap}
          trend={{ value: 8.1, label: 'vs last month' }}
        />
        <StatCard
          title="Total Spend"
          value={formatCurrency(overview?.costs.total_cost ?? 0)}
          description={`${overview?.costs.trend ?? 'stable'} trend`}
          icon={DollarSign}
          trend={{ value: 4.3, label: 'vs last month' }}
        />
        <StatCard
          title="Avg Response Time"
          value={`${(overview?.usage.avg_latency ?? 0).toFixed(1)}s`}
          description={`${overview?.tokens.total_tokens ?? 0} total tokens`}
          icon={TrendingUp}
          trend={{ value: -20, label: 'vs last month' }}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <UsageChart data={usageChartData} timeframe="7d" onTimeframeChange={(tf) => console.log('Timeframe:', tf)} />
        </div>
        <div>
          <RecentActivity activities={recentActivities} onViewAll={() => {}} />
        </div>
      </div>

      <CostTracker
        data={costChartData}
        period="week"
        onPeriodChange={(p) => console.log('Period:', p)}
        totalBudget={costAnalytics?.forecast_next_period ?? 140}
      />
    </div>
  );
}
