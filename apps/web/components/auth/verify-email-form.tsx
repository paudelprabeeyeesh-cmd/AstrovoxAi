"use client"
import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Link from "next/link"
import { api } from "@/lib/api"

const verifyEmailSchema = z.object({
  token: z.string().min(1, "Token is required"),
})

type VerifyEmailData = z.infer<typeof verifyEmailSchema>

function VerifyEmailForm({ className, ...props }: React.HTMLAttributes<HTMLFormElement>) {
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [success, setSuccess] = React.useState(false)

  const form = useForm<VerifyEmailData>({
    resolver: zodResolver(verifyEmailSchema),
    defaultValues: { token: "" },
  })

  async function onSubmit(data: VerifyEmailData) {
    setIsLoading(true)
    setError(null)
    try {
      await api.post("/auth/verify", { token: data.token })
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed")
    } finally {
      setIsLoading(false)
    }
  }

  if (success) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-center">
        <h3 className="text-lg font-semibold">Email verified</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Your email has been verified successfully.
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
    )
  }

  return (
    <form className={cn("space-y-4", className)} onSubmit={form.handleSubmit(onSubmit)} {...props}>
      <div className="space-y-2">
        <Label htmlFor="token">Verification token</Label>
        <Input id="token" placeholder="Paste your token" disabled={isLoading} {...form.register("token")} />
        {form.formState.errors.token && <p className="text-sm text-destructive">{form.formState.errors.token.message}</p>}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? "Verifying..." : "Verify email"}
      </Button>
    </form>
  )
}

export { VerifyEmailForm }
