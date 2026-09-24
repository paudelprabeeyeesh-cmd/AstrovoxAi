"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"

export default function ChatError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error("Chat page error:", error)
  }, [error])

  return (
    <div className="flex h-full flex-col items-center justify-center space-y-4 p-8">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold">Something went wrong!</h2>
        <p className="text-muted-foreground max-w-md">
          We couldn&apos;t load the chat. This might be a temporary issue.
        </p>
        {error.message && (
          <p className="text-sm text-destructive font-mono bg-destructive/10 p-2 rounded">
            {error.message}
          </p>
        )}
      </div>
      <Button onClick={reset} variant="outline">
        Try again
      </Button>
    </div>
  )
}
