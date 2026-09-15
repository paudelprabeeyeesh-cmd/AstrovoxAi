'use client';

import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface UsageDataPoint {
  date: string;
  tokens: number;
  cost: number;
}

interface UsageChartProps {
  data: UsageDataPoint[];
  timeframe?: '7d' | '30d' | '90d';
  onTimeframeChange?: (timeframe: '7d' | '30d' | '90d') => void;
}

const timeframeLabels = {
  '7d': '7 days',
  '30d': '30 days',
  '90d': '90 days',
};

export function UsageChart({ data, timeframe = '30d', onTimeframeChange }: UsageChartProps) {
  const filteredData = useMemo(() => {
    const days = timeframe === '7d' ? 7 : timeframe === '30d' ? 30 : 90;
    return data.slice(-days);
  }, [data, timeframe]);

  const formatYAxis = (value: number) => {
    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
    if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
    return value.toString();
  };

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Token Usage</h3>
          <p className="text-sm text-muted-foreground">Monitor your API consumption</p>
        </div>
        <div className="flex rounded-md bg-muted p-1">
          {(Object.keys(timeframeLabels) as Array<keyof typeof timeframeLabels>).map((key) => {
            const isActive = timeframe === key;
            return (
              <button
                key={key}
                onClick={() => onTimeframeChange?.(key)}
                className={isActive ? 'rounded-sm px-3 py-1 text-sm font-medium transition-colors bg-background text-foreground shadow-sm' : 'rounded-sm px-3 py-1 text-sm font-medium transition-colors text-muted-foreground hover:text-foreground'}
              >
                {timeframeLabels[key]}
              </button>
            );
          })}
        </div>
      </div>
      <div className="mt-6 h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={filteredData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} axisLine={{ stroke: 'hsl(var(--border))' }} tickLine={{ stroke: 'hsl(var(--border))' }} />
            <YAxis tickFormatter={formatYAxis} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} axisLine={{ stroke: 'hsl(var(--border))' }} tickLine={{ stroke: 'hsl(var(--border))' }} />
            <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '0.5rem' }} labelStyle={{ color: 'hsl(var(--foreground))' }} />
            <Legend />
            <Line type="monotone" dataKey="tokens" name="Tokens" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey="cost" name="Cost ($)" stroke="hsl(var(--ring))" strokeWidth={2} dot={false} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}