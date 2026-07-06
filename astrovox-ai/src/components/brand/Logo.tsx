import { cn } from "@/lib/utils";

export function AstroMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={cn("h-8 w-8", className)}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="astro-g" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="oklch(0.78 0.18 295)" />
          <stop offset="100%" stopColor="oklch(0.82 0.14 200)" />
        </linearGradient>
      </defs>
      <path
        d="M16 2.5c1.1 3.6 3.4 6 7 7.2-3.6 1.2-5.9 3.6-7 7.2-1.1-3.6-3.4-6-7-7.2 3.6-1.2 5.9-3.6 7-7.2Z"
        fill="url(#astro-g)"
      />
      <circle cx="23.5" cy="22.5" r="2.2" fill="url(#astro-g)" />
      <circle cx="8" cy="24" r="1.4" fill="url(#astro-g)" opacity="0.7" />
      <circle cx="14" cy="28" r="1" fill="url(#astro-g)" opacity="0.5" />
    </svg>
  );
}

export function AstroWordmark({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <AstroMark />
      <span className="font-display text-lg font-semibold tracking-tight" style={{ fontFamily: "var(--font-display)" }}>
        Astrovox<span className="text-gradient-aurora">AI</span>
      </span>
    </div>
  );
}