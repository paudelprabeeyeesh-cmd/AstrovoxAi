"use client"
import * as React from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { AuthForm } from "./auth-form"

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
})

type LoginFormData = z.infer<typeof loginSchema>

interface LoginFormProps extends React.HTMLAttributes<HTMLFormElement> {
  onSuccess?: () => void
}

function LoginForm({ className, onSuccess, ...props }: LoginFormProps) {
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const form = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  })

  async function onSubmit(data: LoginFormData) {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/auth/signin/email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      })
      if (!res.ok) {
        const err = await res.json()
        setError(err.message || "Something went wrong")
        return
      }
      onSuccess?.()
    } catch {
      setError("Something went wrong")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthForm>
      <form className={cn("space-y-4", className)} onSubmit={form.handleSubmit(onSubmit)} {...props}>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" placeholder="name@example.com" disabled={isLoading} {...form.register("email")} />
          {form.formState.errors.email && <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" disabled={isLoading} {...form.register("password")} />
          {form.formState.errors.password && <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>}
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </AuthForm>
  )
}

export { LoginForm }
