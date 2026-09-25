'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, ArrowLeft, Play, CheckCircle2, Circle } from 'lucide-react';
import { api } from '@/lib/api';
import { Tutorial, TutorialProgress } from '@/lib/api';
import Link from 'next/link';

export default function TutorialDetailPage() {
  const params = useParams();
  const tutorialId = params.id as string;
  const [tutorial, setTutorial] = useState<Tutorial | null>(null);
  const [progress, setProgress] = useState<TutorialProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    loadTutorial();
  }, [tutorialId]);

  const loadTutorial = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ tutorial: Tutorial }>(`/support/tutorials/${tutorialId}`);
      setTutorial(data.tutorial);
      const progressData = await api.get<{ progress: TutorialProgress[] }>('/support/tutorials/progress');
      const userProgress = progressData.progress?.find((p: TutorialProgress) => p.tutorial_id === tutorialId);
      if (userProgress) {
        setProgress(userProgress);
        setCurrentStep(userProgress.current_step);
        setCompleted(userProgress.completed);
      }
    } catch {
      setTutorial(null);
    } finally {
      setLoading(false);
    }
  };

  const startTutorial = async () => {
    await api.post(`/support/tutorials/${tutorialId}/start`, null);
    setProgress({
      id: '',
      user_id: '',
      tutorial_id: tutorialId,
      current_step: 0,
      completed: false,
      started_at: Date.now(),
    });
  };

  const nextStep = async () => {
    const next = currentStep + 1;
    setCurrentStep(next);
    const data = await api.post<{ progress: TutorialProgress }>(`/support/tutorials/${tutorialId}/progress`, { currentStep: next });
    if (data.progress?.completed) {
      setCompleted(true);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!tutorial) {
    return (
      <div className="space-y-6">
        <Link href="/tutorials">
          <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-2" />Back to Tutorials</Button>
        </Link>
        <Card className="p-12 text-center">
          <h3 className="text-lg font-medium">Tutorial not found</h3>
        </Card>
      </div>
    );
  }

  const step = tutorial.steps[currentStep];

  return (
    <div className="space-y-6 max-w-3xl">
      <Link href="/tutorials">
        <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-2" />Back to Tutorials</Button>
      </Link>

      <Card className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <Badge variant="secondary" className="mb-2 capitalize">{tutorial.difficulty}</Badge>
            <h1 className="text-2xl font-bold">{tutorial.title}</h1>
            <p className="text-muted-foreground mt-1">{tutorial.description}</p>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1"><BookOpen className="h-4 w-4" /> {tutorial.steps.length} steps</span>
          <span className="flex items-center gap-1"><Clock className="h-4 w-4" /> {tutorial.estimated_time} min</span>
        </div>

        {!progress && !completed && (
          <Button className="mt-6" onClick={startTutorial}>
            <Play className="h-4 w-4 mr-2" />Start Tutorial
          </Button>
        )}

        {progress && !completed && (
          <div className="mt-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Step {currentStep + 1} of {tutorial.steps.length}</span>
              <Badge variant="outline">{Math.round(((currentStep) / tutorial.steps.length) * 100)}%</Badge>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-primary h-2 rounded-full transition-all" style={{ width: `${(currentStep / tutorial.steps.length) * 100}%` }} />
            </div>
            {step && (
              <Card className="p-4 mt-4">
                <h3 className="font-semibold mb-2">{String(step.title || `Step ${currentStep + 1}`)}</h3>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap">{String(step.content || step)}</p>
              </Card>
            )}
            <div className="flex gap-2">
              <Button onClick={nextStep} disabled={currentStep >= tutorial.steps.length - 1}>
                Next Step
              </Button>
            </div>
          </div>
        )}

        {completed && (
          <Card className="p-6 mt-6 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium">Tutorial Completed!</h3>
            <p className="text-muted-foreground">Great job! You have finished this tutorial.</p>
          </Card>
        )}

        <div className="mt-6">
          <h3 className="font-semibold mb-3">All Steps</h3>
          <div className="space-y-2">
            {tutorial.steps.map((s, idx) => (
              <div key={idx} className="flex items-center gap-2 text-sm">
                {idx <= currentStep || completed ? (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                ) : (
                  <Circle className="h-4 w-4 text-muted-foreground" />
                )}
                <span className={idx <= currentStep || completed ? '' : 'text-muted-foreground'}>
                  {String(s.title || `Step ${idx + 1}`)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}
