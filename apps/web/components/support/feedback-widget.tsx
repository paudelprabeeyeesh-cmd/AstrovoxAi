'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, X, MessageSquare } from 'lucide-react';
import { api } from '@/lib/api';

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState('general');
  const [rating, setRating] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await api.post('/support/feedback', { type, rating, comment, page_url: window.location.pathname });
      setOpen(false);
      setComment('');
      setRating(null);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="fixed bottom-4 left-4 z-50 shadow-lg"
        onClick={() => setOpen(!open)}
      >
        <MessageSquare className="h-4 w-4 mr-2" />Feedback
      </Button>

      {open && (
        <Card className="fixed bottom-16 left-4 z-50 w-80 p-4 shadow-xl">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">Send Feedback</h3>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium mb-1 block">Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
              >
                <option value="general">General</option>
                <option value="bug">Bug</option>
                <option value="feature">Feature Request</option>
                <option value="usability">Usability</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium mb-1 block">Rating (1-5)</label>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Button
                    key={n}
                    variant={rating === n ? 'default' : 'ghost'}
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => setRating(n)}
                  >
                    {n}
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-xs font-medium mb-1 block">Comment</label>
              <Textarea
                placeholder="Tell us what you think..."
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                className="text-sm"
              />
            </div>

            <Button className="w-full" size="sm" onClick={handleSubmit} disabled={submitting}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit Feedback'}
            </Button>
          </div>
        </Card>
      )}
    </>
  );
}
