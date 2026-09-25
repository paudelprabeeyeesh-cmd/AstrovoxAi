'use client';

import { cn } from '@/lib/utils';

interface LogoProps {
  className?: string;
  showText?: boolean;
}

export function Logo({ className, showText = true }: LogoProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <svg
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="size-8"
        aria-hidden="true"
      >
        <circle cx="16" cy="16" r="14" stroke="currentColor" strokeWidth="2" />
        <path
          d="M16 8L10 16L16 24L22 16L16 8Z"
          fill="currentColor"
          opacity="0.2"
        />
        <path
          d="M16 8L10 16L16 24L22 16L16 8Z"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <circle cx="16" cy="16" r="3" fill="currentColor" />
      </svg>

      {showText && (
        <span className="font-bold text-xl tracking-tight">
          Astrovox<span className="text-primary">AI</span>
        </span>
      )}
    </div>
  );
}
