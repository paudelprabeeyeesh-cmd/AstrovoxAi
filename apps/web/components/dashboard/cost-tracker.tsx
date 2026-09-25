'use client';

import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { TrendingUp, TrendingDown, DollarSign } from 'lucide-react';

interface CostDataPoint {
  period: string;
  amount: number;
  budget?: number;
}

interface CostTrackerProps {
  data: CostDataPoint[];
  period?: 'day' | 'week' | 'month';
  onPeriodChange?: (period: 'day' | 'week' | 'month') => void;
  totalBudget?: number;
}

const periodLabels = {
  day: 'Daily',
  week: 'Weekly',
  month: 'Monthly',
};

export function CostTracker({ data, period = 'week', onPeriodChange, totalBudget }: CostTrackerProps) {
  const totalSpent = useMemo(() => data.reduce((sum, item) => sum + item.amount, 0), [data]);
  const averageSpent = useMemo(() => (data.length === 0 ? 0 : totalSpent / data.length), [data, totalSpent]);
  const budgetPercentage = useMemo(() => {
    if (!totalBudget || totalBudget === 0) return 0;
    return Math.min((totalSpent / totalBudget) * 100, 100);
  }, [totalSpent, totalBudget]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value);
  };

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Cost Tracker</h3>
          <p className="text-sm text-muted-foreground">Track spending across periods</p>
        </div>
        <div className="flex rounded-md bg-muted p-1">
          {(Object.keys(periodLabels) as Array<'day' | 'week' | 'month'>).map((key) => (
            <button
              key={key}
              onClick={() => onPeriodChange?.(key)}
              className={period === key ? 'rounded-sm px-3 py-1 text-sm font-medium transition-colors bg-background text-foreground shadow-sm' : 'rounded-sm px-3 py-1 text-sm font-medium transition-colors text-muted-foreground hover:text-foreground'}
            >
              {periodLabels[key]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-4">
          <div className="rounded-full bg-primary/10 p-2">
            <DollarSign className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Total Spent</p>
            <p className="text-xl font-bold">{formatCurrency(totalSpent)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-4">
          <div className="rounded-full bg-primary/10 p-2">
            <TrendingUp className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Average</p>
            <p className="text-xl font-bold">{formatCurrency(averageSpent)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-lg bg-muted/50 p-4">
          <div className="rounded-full bg-primary/10 p-2">
            <TrendingDown className="h-5 w-5 text-primary" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Budget</p>
            <p className="text-xl font-bold">{totalBudget ? formatCurrency(totalBudget) : 'N/A'}</p>
          </div>
        </div>
      </div>

      {totalBudget && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Budget Used</span>
            <span className="font-medium">{budgetPercentage.toFixed(1)}%</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-primary transition-all" style={{ width: budgetPercentage + '%' }} />
          </div>
        </div>
      )}

      <div className="mt-6 h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="period" tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} axisLine={{ stroke: 'hsl(var(--border))' }} tickLine={{ stroke: 'hsl(var(--border))' }} />
            <YAxis tickFormatter={(v) => "$" + v} />
            <Tooltip contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '0.5rem' }} labelStyle={{ color: 'hsl(var(--foreground))' }} formatter={(value: number) => [formatCurrency(value), 'Amount']} />
            <Legend />
            <Bar dataKey="amount" name="Spent" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            {totalBudget && <Bar dataKey="budget" name="Budget" fill="hsl(var(--muted-foreground))" radius={[4, 4, 0, 0]} />}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}



