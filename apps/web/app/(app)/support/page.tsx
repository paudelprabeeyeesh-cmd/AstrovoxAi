'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Plus, Ticket, Bug, Lightbulb, MessageSquare } from 'lucide-react';
import { api } from '@/lib/api';
import Link from 'next/link';

export default function SupportPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Support</h1>
        <p className="text-muted-foreground">Get help, report issues, and track your requests.</p>
      </div>

      <Tabs defaultValue="tickets" className="space-y-4">
        <TabsList>
          <TabsTrigger value="tickets" className="gap-2"><Ticket className="h-4 w-4" />Tickets</TabsTrigger>
          <TabsTrigger value="bugs" className="gap-2"><Bug className="h-4 w-4" />Bug Reports</TabsTrigger>
          <TabsTrigger value="features" className="gap-2"><Lightbulb className="h-4 w-4" />Feature Requests</TabsTrigger>
        </TabsList>

        <TabsContent value="tickets">
          <TicketsTab />
        </TabsContent>
        <TabsContent value="bugs">
          <BugsTab />
        </TabsContent>
        <TabsContent value="features">
          <FeaturesTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function TicketsTab() {
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('medium');

  useEffect(() => {
    loadTickets();
  }, []);

  const loadTickets = async () => {
    setLoading(true);
    try {
      const data = await api.get<any>('/support/tickets');
      setTickets(data.tickets || []);
    } catch {
      setTickets([]);
    } finally {
      setLoading(false);
    }
  };

  const createTicket = async () => {
    await api.post('/support/tickets', { subject, description, priority, category: 'general' });
    setShowForm(false);
    setSubject('');
    setDescription('');
    loadTickets();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Your Tickets</h2>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />New Ticket
        </Button>
      </div>

      {showForm && (
        <Card className="p-4 space-y-3">
          <Input placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
          <Textarea placeholder="Describe your issue..." value={description} onChange={(e) => setDescription(e.target.value)} />
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <div className="flex gap-2">
            <Button onClick={createTicket} disabled={!subject || !description}>Create Ticket</Button>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : tickets.length === 0 ? (
        <Card className="p-8 text-center">
          <Ticket className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No tickets yet.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {tickets.map((ticket) => (
            <Card key={ticket.id} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-sm">{ticket.subject}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{ticket.description.slice(0, 100)}...</p>
                </div>
                <div className="flex gap-2">
                  <Badge variant={ticket.priority === 'high' || ticket.priority === 'critical' ? 'destructive' : 'secondary'}>{ticket.priority}</Badge>
                  <Badge variant="outline">{ticket.status}</Badge>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function BugsTab() {
  const [bugs, setBugs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState('medium');

  useEffect(() => {
    loadBugs();
  }, []);

  const loadBugs = async () => {
    setLoading(true);
    try {
      const data = await api.getBugReports();
      setBugs(data.bugs || []);
    } catch {
      setBugs([]);
    } finally {
      setLoading(false);
    }
  };

  const createBug = async () => {
    await api.createBugReport(title, description, severity);
    setShowForm(false);
    setTitle('');
    setDescription('');
    loadBugs();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Bug Reports</h2>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />Report Bug
        </Button>
      </div>

      {showForm && (
        <Card className="p-4 space-y-3">
          <Input placeholder="Bug title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <Textarea placeholder="Describe the bug..." value={description} onChange={(e) => setDescription(e.target.value)} />
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <div className="flex gap-2">
            <Button onClick={createBug} disabled={!title || !description}>Submit Report</Button>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : bugs.length === 0 ? (
        <Card className="p-8 text-center">
          <Bug className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No bug reports yet.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {bugs.map((bug) => (
            <Card key={bug.id} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-sm">{bug.title}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{bug.description.slice(0, 100)}...</p>
                </div>
                <div className="flex gap-2">
                  <Badge variant={bug.severity === 'high' || bug.severity === 'critical' ? 'destructive' : 'secondary'}>{bug.severity}</Badge>
                  <Badge variant="outline">{bug.status}</Badge>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function FeaturesTab() {
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    loadRequests();
  }, []);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const data = await api.getFeatureRequests();
      setRequests(data.requests || []);
    } catch {
      setRequests([]);
    } finally {
      setLoading(false);
    }
  };

  const createRequest = async () => {
    await api.createFeatureRequest(title, description);
    setShowForm(false);
    setTitle('');
    setDescription('');
    loadRequests();
  };

  const vote = async (id: string) => {
    await api.voteFeatureRequest(id);
    loadRequests();
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Feature Requests</h2>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-2" />Request Feature
        </Button>
      </div>

      {showForm && (
        <Card className="p-4 space-y-3">
          <Input placeholder="Feature title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <Textarea placeholder="Describe the feature..." value={description} onChange={(e) => setDescription(e.target.value)} />
          <div className="flex gap-2">
            <Button onClick={createRequest} disabled={!title || !description}>Submit Request</Button>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : requests.length === 0 ? (
        <Card className="p-8 text-center">
          <Lightbulb className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No feature requests yet.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {requests.map((req) => (
            <Card key={req.id} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-medium text-sm">{req.title}</h3>
                  <p className="text-xs text-muted-foreground mt-1">{req.description.slice(0, 100)}...</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={() => vote(req.id)}>
                    <MessageSquare className="h-4 w-4 mr-1" />{req.votes}
                  </Button>
                  <Badge variant="outline">{req.status}</Badge>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
