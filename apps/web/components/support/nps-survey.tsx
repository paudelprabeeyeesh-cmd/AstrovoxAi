'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Loader2, Star, X } from 'lucide-react';
import { api } from '@/lib/api';

interface NpsSurveyProps {
  onComplete?: () => void;
}

export function NpsSurvey({ onComplete }: NpsSurveyProps) {
  const [open, setOpen] = useState(false);
  const [score, setScore] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      const dismissed = localStorage.getItem('nps_dismissed');
      if (!dismissed) {
        setOpen(true);
      }
    }, 5000);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = async () => {
    if (score === null) return;
    setSubmitting(true);
    try {
      await api.submitNps(score, comment, 'in-app');
      setSubmitted(true);
      onComplete?.();
      setTimeout(() => setOpen(false), 2000);
    } catch {
      // ignore
    } finally {
      setSubmitting(false);
    }
  };

  const dismiss = () => {
    setOpen(false);
    localStorage.setItem('nps_dismissed', 'true');
  };

  if (!open) return null;

  if (submitted) {
    return (
      <Card className="fixed bottom-20 right-4 z-50 w-80 p-4 shadow-xl">
        <p className="text-sm text-center">Thank you for your feedback!</p>
      </Card>
    );
  }

  return (
    <Card className="fixed bottom-20 right-4 z-50 w-80 p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm">How likely are you to recommend us?</h3>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={dismiss}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex gap-1 mb-3">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
          <Button
            key={n}
            variant={score === n ? 'default' : 'ghost'}
            size="sm"
            className="h-8 w-8 p-0 text-xs"
            onClick={() => setScore(n)}
          >
            {n}
          </Button>
        ))}
      </div>
      <Input
        placeholder="Add a comment (optional)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        className="mb-3 text-sm"
      />
      <Button className="w-full" size="sm" onClick={handleSubmit} disabled={score === null || submitting}>
        {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Submit'}
      </Button>
    </Card>
  );
}
