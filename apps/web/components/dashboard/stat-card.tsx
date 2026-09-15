'use client';

import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    label: string;
  };
}

export function StatCard({ title, value, description, icon: Icon, trend }: StatCardProps) {
  const trendColor = trend && trend.value > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
  const trendIcon = trend && trend.value > 0 ? '?' : '?';

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <div className="rounded-md bg-primary/10 p-2">
          <Icon className="h-5 w-5 text-primary" />
        </div>
      </div>
      <div className="mt-4">
        <div className="text-3xl font-bold tracking-tight">{value}</div>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
        {trend && (
          <div className={`mt-2 flex items-center text-sm ${trendColor}`}>
            <span className="font-medium">{trendIcon} {Math.abs(trend.value)}%</span>
            <span className="ml-1 text-muted-foreground">{trend.label}</span>
          </div>
        )}
      </div>
    </div>
  );
}
