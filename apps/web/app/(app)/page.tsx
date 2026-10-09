'use client';

import Link from 'next/link';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MessageSquare, Zap, Brain, Shield, ArrowRight } from 'lucide-react';

const appSections = [
  {
    title: 'Dashboard',
    description: 'Overview, usage stats, and recent activity.',
    href: '/dashboard',
    icon: Brain,
    badge: 'Main',
  },
  {
    title: 'Chat',
    description: 'Start conversations, manage history and folders.',
    href: '/chat',
    icon: MessageSquare,
    badge: 'Core',
  },
  {
    title: 'Models',
    description: 'Browse and configure available AI models.',
    href: '/models',
    icon: Zap,
    badge: 'New',
  },
  {
    title: 'Admin',
    description: 'Users, roles, permissions, and audit settings.',
    href: '/admin',
    icon: Shield,
    badge: 'Restricted',
  },
];

export default function AppHomePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">App</h1>
        <p className="text-muted-foreground">Choose a a section to open.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {appSections.map((section) => {
          const Icon = section.icon;
          return (
            <Card
              key={section.title}
              className="p-5 transition-shadow hover:shadow-md"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="rounded-lg bg-primary/10 p-2">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <Badge variant="outline" className="text-xs">
                  {section.badge}
                </Badge>
              </div>
              <h2 className="font-semibold text-sm mb-1">{section.title}</h2>
              <p className="text-xs text-muted-foreground mb-4 line-clamp-2">
                {section.description}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="w-full"
                asChild
              >
                <Link href={section.href}>
                  Open <ArrowRight className="ml-2 h-3 w-3" />
                </Link>
              </Button>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
