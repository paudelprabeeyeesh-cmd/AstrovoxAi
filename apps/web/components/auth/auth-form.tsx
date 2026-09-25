"use client"
import * as React from "react"
import { cn } from "@/lib/utils"

function AuthForm({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("w-full max-w-[400px] space-y-6 rounded-xl border border-border bg-card p-8 shadow-sm", className)}
      {...props}
    />
  )
}

export { AuthForm }
