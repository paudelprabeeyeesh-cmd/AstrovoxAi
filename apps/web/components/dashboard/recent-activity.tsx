'use client';

import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ActivityItem {
  id: string;
  title: string;
  description: string;
  timestamp: Date;
  type: 'chat' | 'api' | 'billing' | 'system';
  icon?: LucideIcon;
}

interface RecentActivityProps {
  activities: ActivityItem[];
  maxItems?: number;
  onViewAll?: () => void;
}

const typeColors = {
  chat: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  api: 'bg-green-500/10 text-green-600 dark:text-green-400',
  billing: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  system: 'bg-gray-500/10 text-gray-600 dark:text-gray-400',
};

import { MessageSquare, Zap, CreditCard, Settings } from 'lucide-react';

const defaultIcons: Record<string, LucideIcon> = {
  chat: MessageSquare,
  api: Zap,
  billing: CreditCard,
  system: Settings,
};

function formatTimestamp(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `m ago`;
  if (hours < 24) return `h ago`;
  if (days < 7) return `d ago`;
  return date.toLocaleDateString();
}

export function RecentActivity({ activities, maxItems = 5, onViewAll }: RecentActivityProps) {
  const displayActivities = activities.slice(0, maxItems);

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Recent Activity</h3>
          <p className="text-sm text-muted-foreground">Latest conversations and events</p>
        </div>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-sm font-medium text-primary hover:underline"
          >
            View all
          </button>
        )}
      </div>
      <div className="mt-6 space-y-4">
        {displayActivities.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="rounded-full bg-muted p-3">
              <defaultIcons.system className="h-6 w-6 text-muted-foreground" />
            </div>
            <p className="mt-3 text-sm font-medium text-muted-foreground">No recent activity</p>
            <p className="text-xs text-muted-foreground">Your activity will appear here</p>
          </div>
        ) : (
          displayActivities.map((activity) => {
            const Icon = activity.icon || defaultIcons[activity.type] || defaultIcons.system;
            return (
              <div
                key={activity.id}
                className="flex items-start gap-4 rounded-lg border border-border/50 p-4 transition-colors hover:bg-muted/30"
              >
                <div className={cn('rounded-md p-2', typeColors[activity.type])}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{activity.title}</p>
                  <p className="text-sm text-muted-foreground line-clamp-1">{activity.description}</p>
                </div>
                <time className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatTimestamp(activity.timestamp)}
                </time>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
