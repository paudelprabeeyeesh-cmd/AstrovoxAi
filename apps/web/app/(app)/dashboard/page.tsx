'use client';

import { StatCard } from '@/components/dashboard/stat-card';
import { UsageChart } from '@/components/dashboard/usage-chart';
import { CostTracker } from '@/components/dashboard/cost-tracker';
import { RecentActivity } from '@/components/dashboard/recent-activity';
import { MessageSquare, Zap, DollarSign, TrendingUp } from 'lucide-react';

const usageData = [
  { date: '2026-09-08', tokens: 4200, cost: 0.12 },
  { date: '2026-09-09', tokens: 5100, cost: 0.15 },
  { date: '2026-09-10', tokens: 3800, cost: 0.11 },
  { date: '2026-09-11', tokens: 6200, cost: 0.18 },
  { date: '2026-09-12', tokens: 7500, cost: 0.22 },
  { date: '2026-09-13', tokens: 8900, cost: 0.26 },
  { date: '2026-09-14', tokens: 6700, cost: 0.20 },
];

const costData = [
  { period: 'Mon', amount: 12.5, budget: 20 },
  { period: 'Tue', amount: 18.2, budget: 20 },
  { period: 'Wed', amount: 15.0, budget: 20 },
  { period: 'Thu', amount: 22.4, budget: 20 },
  { period: 'Fri', amount: 19.8, budget: 20 },
  { period: 'Sat', amount: 14.1, budget: 20 },
  { period: 'Sun', amount: 16.5, budget: 20 },
];

const recentActivities = [
  { id: '1', title: 'New conversation started', description: 'Started a chat about React Hooks', timestamp: new Date(Date.now() - 1000 * 60 * 5), type: 'chat' as const },
  { id: '2', title: 'API usage spike', description: 'Token usage exceeded daily threshold', timestamp: new Date(Date.now() - 1000 * 60 * 30), type: 'api' as const },
  { id: '3', title: 'Invoice paid', description: 'Payment for September processed successfully', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), type: 'billing' as const },
  { id: '4', title: 'System update', description: 'New features deployed to production', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 5), type: 'system' as const },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back! Here is your overview.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Conversations" value="1,284" description="+12% from last month" icon={MessageSquare} trend={{ value: 12, label: 'vs last month' }} />
        <StatCard title="API Calls" value="45.2K" description="+8.1% from last month" icon={Zap} trend={{ value: 8.1, label: 'vs last month' }} />
        <StatCard title="Total Spend" value="$124.50" description="+4.3% from last month" icon={DollarSign} trend={{ value: 4.3, label: 'vs last month' }} />
        <StatCard title="Avg Response Time" value="1.2s" description="-0.3s from last month" icon={TrendingUp} trend={{ value: -20, label: 'vs last month' }} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <UsageChart data={usageData} timeframe="7d" onTimeframeChange={(tf) => console.log('Timeframe:', tf)} />
        </div>
        <div>
          <RecentActivity activities={recentActivities} onViewAll={() => {}} />
        </div>
      </div>

      <CostTracker data={costData} period="week" onPeriodChange={(p) => console.log('Period:', p)} totalBudget={140} />
    </div>
  );
}
