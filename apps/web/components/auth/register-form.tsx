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

const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string().min(8, "Password must be at least 8 characters"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
})

type RegisterFormData = z.infer<typeof registerSchema>

interface RegisterFormProps extends React.HTMLAttributes<HTMLFormElement> {
  onSuccess?: () => void
}

function RegisterForm({ className, onSuccess, ...props }: RegisterFormProps) {
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const form = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: { name: "", email: "", password: "", confirmPassword: "" },
  })

  async function onSubmit(data: RegisterFormData) {
    setIsLoading(true)
    setError(null)
    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: data.name, email: data.email, password: data.password }),
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
          <Label htmlFor="name">Name</Label>
          <Input id="name" placeholder="John Doe" disabled={isLoading} {...form.register("name")} />
          {form.formState.errors.name && <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>}
        </div>
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
        <div className="space-y-2">
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <Input id="confirmPassword" type="password" disabled={isLoading} {...form.register("confirmPassword")} />
          {form.formState.errors.confirmPassword && <p className="text-sm text-destructive">{form.formState.errors.confirmPassword.message}</p>}
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "Creating account..." : "Create account"}
        </Button>
      </form>
    </AuthForm>
  )
}

export { RegisterForm }
