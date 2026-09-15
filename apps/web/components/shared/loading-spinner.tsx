"use client";

import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: number;
  className?: string;
  label?: string;
}

export function LoadingSpinner({ size = 24, className, label = "Loading..." }: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2" role="status" aria-live="polite">
      <Loader2 className={cn("animate-spin text-primary", className)} size={size} />
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  );
}
