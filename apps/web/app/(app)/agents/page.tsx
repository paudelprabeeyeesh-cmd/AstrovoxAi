'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Bot, Play, Settings, Zap } from 'lucide-react';

const agents = [
  { id: 'planner', name: 'Planner', description: 'Creates plans and breaks down tasks', capabilities: ['planning', 'task-breakdown', 'scheduling'] },
  { id: 'coder', name: 'Coder', description: 'Generates and implements code solutions', capabilities: ['coding', 'implementation', 'debugging'] },
  { id: 'researcher', name: 'Researcher', description: 'Conducts research and gathers information', capabilities: ['research', 'analysis', 'sources'] },
  { id: 'writer', name: 'Writer', description: 'Creates and polishes written content', capabilities: ['writing', 'editing', 'style'] },
  { id: 'reviewer', name: 'Reviewer', description: 'Reviews outputs for quality and accuracy', capabilities: ['review', 'quality', 'feedback'] },
  { id: 'debugger', name: 'Debugger', description: 'Identifies and fixes errors', capabilities: ['debugging', 'troubleshooting', 'fixes'] },
];

export default function AgentsPage() {
  const [selectedAgent, setSelectedAgent] = useState(agents[0]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
        <p className="text-muted-foreground">Select and configure AI agents for your workflows.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 grid gap-4 sm:grid-cols-2">
          {agents.map((agent) => (
            <Card
              key={agent.id}
              className={`p-4 cursor-pointer hover:shadow-md transition-shadow ${
                selectedAgent.id === agent.id ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => setSelectedAgent(agent)}
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium">{agent.name}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{agent.description}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {agent.capabilities.map((cap) => (
                      <Badge key={cap} variant="outline" className="text-xs">{cap}</Badge>
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>

        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium flex items-center gap-2">
              <Settings className="h-4 w-4" />
              {selectedAgent.name} Settings
            </h3>
            <Badge variant="secondary">Active</Badge>
          </div>
          <p className="text-sm text-muted-foreground mb-4">{selectedAgent.description}</p>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Model</label>
              <select className="w-full mt-1 rounded-md border bg-background px-3 py-2 text-sm">
                <option>gpt-4o</option>
                <option>claude-3.5-sonnet</option>
                <option>gemini-1.5-pro</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Temperature</label>
              <input type="range" min="0" max="1" step="0.1" defaultValue="0.7" className="w-full mt-1" />
            </div>
            <Button className="w-full">
              <Play className="h-4 w-4 mr-2" />
              Run Agent
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
