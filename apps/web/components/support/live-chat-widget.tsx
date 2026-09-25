'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, X, Send, MessageSquare, Bot } from 'lucide-react';
import { api } from '@/lib/api';
import { LiveChatSession, ChatMessage } from '@/lib/api';

export function LiveChatWidget() {
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState<LiveChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && !session) {
      startSession();
    }
  }, [open]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startSession = async () => {
    setLoading(true);
    try {
      const data = await api.post<{ session: LiveChatSession }>('/support/chat/sessions', {});
      setSession(data.session);
      await loadMessages(data.session.id);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (sessionId: string) => {
    try {
      const data = await api.get<{ messages: ChatMessage[] }>(`/support/chat/sessions/${sessionId}/messages`);
      setMessages(data.messages || []);
    } catch {
      // ignore
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !session) return;
    setSending(true);
    try {
      const data = await api.post<{ message: ChatMessage }>(`/support/chat/sessions/${session.id}/messages`, { message: input });
      setMessages((prev) => [...prev, data.message]);
      setInput('');
    } catch {
      // ignore
    } finally {
      setSending(false);
    }
  };

  const endSession = async () => {
    if (!session) return;
    await api.post(`/support/chat/sessions/${session.id}/end`, {});
    setOpen(false);
    setSession(null);
    setMessages([]);
  };

  if (!open) {
    return (
      <Button
        variant="default"
        size="sm"
        className="fixed bottom-4 right-20 z-50 shadow-lg"
        onClick={() => setOpen(true)}
      >
        <MessageSquare className="h-4 w-4 mr-2" />Live Chat
      </Button>
    );
  }

  return (
    <Card className="fixed bottom-4 right-4 z-50 w-96 h-[500px] shadow-xl flex flex-col">
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-primary" />
          <span className="font-semibold text-sm">Support Chat</span>
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={endSession}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <ScrollArea className="flex-1 p-3">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.sender_type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                    msg.sender_type === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {msg.message}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </ScrollArea>

      <div className="p-3 border-t">
        <div className="flex gap-2">
          <Input
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            disabled={sending}
          />
          <Button size="icon" onClick={sendMessage} disabled={sending || !input.trim()}>
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </Card>
  );
}
