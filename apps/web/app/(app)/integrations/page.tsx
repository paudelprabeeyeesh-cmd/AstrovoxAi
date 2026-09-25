'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Plug, Plus, Check, Trash2 } from 'lucide-react';

const integrations = [
  { id: 'github', name: 'GitHub', description: 'Connect repositories and manage issues', connected: true, icon: '🐙' },
  { id: 'docker', name: 'Docker', description: 'Manage containers and images', connected: false, icon: '🐳' },
  { id: 'google_drive', name: 'Google Drive', description: 'Access and sync files', connected: true, icon: '📁' },
  { id: 'slack', name: 'Slack', description: 'Send messages and notifications', connected: false, icon: '💬' },
  { id: 'notion', name: 'Notion', description: 'Manage pages and databases', connected: false, icon: '📝' },
  { id: 'jira', name: 'Jira', description: 'Track issues and projects', connected: false, icon: '📋' },
  { id: 'calendar', name: 'Calendar', description: 'Sync events and schedules', connected: true, icon: '📅' },
  { id: 'email', name: 'Email', description: 'Send and receive emails', connected: false, icon: '📧' },
];

export default function IntegrationsPage() {
  const [items, setItems] = useState(integrations);

  const toggleConnection = (id: string) => {
    setItems(items.map(item => (
      item.id === id ? { ...item, connected: !item.connected } : item
    )));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
        <p className="text-muted-foreground">Connect external services to extend agent capabilities.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {items.map((integration) => (
          <Card key={integration.id} className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex gap-3">
                <div className="text-2xl">{integration.icon}</div>
                <div>
                  <h3 className="font-medium">{integration.name}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{integration.description}</p>
                  <Badge variant={integration.connected ? 'default' : 'secondary'} className="mt-2">
                    {integration.connected ? 'Connected' : 'Disconnected'}
                  </Badge>
                </div>
              </div>
              <div className="flex gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleConnection(integration.id)}
                >
                  {integration.connected ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Plug className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card className="p-6 border-dashed">
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Plug className="h-10 w-10 text-muted-foreground mb-3" />
          <h3 className="font-medium mb-1">Add Integration</h3>
          <p className="text-sm text-muted-foreground mb-4 max-w-sm">
            Configure new MCP integrations with custom actions and parameters.
          </p>
          <Button variant="outline">
            <Plus className="h-4 w-4 mr-2" />
            Add Custom Integration
          </Button>
        </div>
      </Card>
    </div>
  );
}
