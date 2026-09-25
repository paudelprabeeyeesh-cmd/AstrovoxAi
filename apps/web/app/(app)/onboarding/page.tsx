'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, CheckCircle2, Circle, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api';
import { OnboardingProgress } from '@/lib/api';

const STEPS = [
  { id: 'welcome', title: 'Welcome', description: 'Get started with AstrovoxAi' },
  { id: 'profile', title: 'Complete Profile', description: 'Set up your profile information' },
  { id: 'first_chat', title: 'First Chat', description: 'Have your first conversation' },
  { id: 'explore', title: 'Explore Features', description: 'Discover what you can do' },
  { id: 'complete', title: 'All Done', description: 'You are ready to go!' },
];

export default function OnboardingPage() {
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    loadProgress();
  }, []);

  const loadProgress = async () => {
    setLoading(true);
    try {
      const data = await api.getOnboardingProgress();
      if (data.progress) {
        setProgress(data.progress);
        setCurrentStepIndex(data.progress.current_step);
      } else {
        await api.startOnboarding();
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const completeStep = async (stepId: string) => {
    await api.completeOnboardingStep(stepId);
    setCurrentStepIndex((prev) => prev + 1);
    if (currentStepIndex >= STEPS.length - 1) {
      await api.completeOnboarding();
    }
    loadProgress();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const currentStep = STEPS[currentStepIndex] || STEPS[0];
  const isCompleted = progress?.completed;

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Welcome to AstrovoxAi</h1>
        <p className="text-muted-foreground">Let us get you set up in just a few steps.</p>
      </div>

      <Card className="p-6">
        {isCompleted ? (
          <div className="text-center py-8">
            <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">You are all set!</h2>
            <p className="text-muted-foreground mb-4">You have completed the onboarding process.</p>
            <Button onClick={() => window.location.href = '/chat'}>Go to Chat</Button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Step {currentStepIndex + 1} of {STEPS.length}</h2>
              <span className="text-sm text-muted-foreground">{Math.round(((currentStepIndex) / STEPS.length) * 100)}%</span>
            </div>

            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all"
                style={{ width: `${(currentStepIndex / STEPS.length) * 100}%` }}
              />
            </div>

            <div className="py-4">
              <h3 className="text-xl font-semibold mb-2">{currentStep.title}</h3>
              <p className="text-muted-foreground">{currentStep.description}</p>
            </div>

            <div className="space-y-2">
              {STEPS.map((step, idx) => (
                <div
                  key={step.id}
                  className={`flex items-center gap-3 p-3 rounded-md ${
                    idx <= currentStepIndex ? 'bg-accent' : 'bg-muted/30'
                  }`}
                >
                  {idx <= currentStepIndex ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <Circle className="h-5 w-5 text-muted-foreground" />
                  )}
                  <div>
                    <p className="font-medium text-sm">{step.title}</p>
                    <p className="text-xs text-muted-foreground">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end">
              <Button onClick={() => completeStep(currentStep.id)}>
                {currentStepIndex === STEPS.length - 1 ? 'Finish' : 'Next'} <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
