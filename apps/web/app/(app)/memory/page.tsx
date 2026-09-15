'use client';

import { Card } from '@/components/ui/card';

const memories = [
  { id: '1', title: 'React Hooks Preference', content: 'Prefers functional components with hooks over class components.', category: 'Preference', createdAt: new Date('2026-09-10') },
  { id: '2', title: 'TypeScript Config', content: 'Uses strict TypeScript with path aliases configured.', category: 'Technical', createdAt: new Date('2026-09-08') },
  { id: '3', title: 'Deployment Target', content: 'Deploys to Vercel with automatic preview deployments.', category: 'Workflow', createdAt: new Date('2026-09-05') },
];

const categoryColors: Record<string, string> = {
  Preference: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  Technical: 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
  Workflow: 'bg-green-500/10 text-green-600 dark:text-green-400',
};

export default function MemoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Memory</h1>
        <p className="text-muted-foreground">View and manage what the AI remembers about your preferences.</p>
      </div>

      <div className="grid gap-4">
        {memories.map((memory) => (
          <Card key={memory.id} className="p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-medium">{memory.title}</h3>
                  <span className={'rounded-full px-2 py-0.5 text-xs font-medium ' + categoryColors[memory.category]}>
                    {memory.category}
                  </span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{memory.content}</p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Added {memory.createdAt.toLocaleDateString()}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
