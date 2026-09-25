'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Workflow, Plus, Play, GitBranch } from 'lucide-react';

const workflows = [
  { id: 'wf-1', name: 'Code Review Pipeline', steps: 4, status: 'active', lastRun: '2 hours ago' },
  { id: 'wf-2', name: 'Research Assistant', steps: 3, status: 'active', lastRun: '1 day ago' },
  { id: 'wf-3', name: 'Content Generator', steps: 5, status: 'draft', lastRun: 'Never' },
  { id: 'wf-4', name: 'Bug Fixer', steps: 6, status: 'active', lastRun: '30 minutes ago' },
];

export default function WorkflowsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Workflows</h1>
          <p className="text-muted-foreground">Build and manage automated agent workflows.</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          New Workflow
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((workflow) => (
          <Card key={workflow.id} className="p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-primary" />
                <h3 className="font-medium">{workflow.name}</h3>
              </div>
              <Badge variant={workflow.status === 'active' ? 'default' : 'secondary'}>
                {workflow.status}
              </Badge>
            </div>
            <div className="flex items-center justify-between text-sm text-muted-foreground mb-4">
              <span>{workflow.steps} steps</span>
              <span>Last run: {workflow.lastRun}</span>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1">
                <Play className="h-3 w-3 mr-1" />
                Run
              </Button>
              <Button variant="ghost" size="sm">
                <Workflow className="h-3 w-3 mr-1" />
                Edit
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <Card className="p-6 border-dashed">
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Workflow className="h-10 w-10 text-muted-foreground mb-3" />
          <h3 className="font-medium mb-1">Visual Workflow Builder</h3>
          <p className="text-sm text-muted-foreground mb-4 max-w-sm">
            Drag and drop agents, conditions, and actions to create powerful automated workflows.
          </p>
          <Button variant="outline">
            <Plus className="h-4 w-4 mr-2" />
            Open Builder
          </Button>
        </div>
      </Card>
    </div>
  );
}
