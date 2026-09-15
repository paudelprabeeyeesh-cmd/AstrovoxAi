"use client";
import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Link from "next/link";
import { api } from "@/lib/api";

const forgotPasswordSchema = z.object({
  email: z.string().email("Invalid email address"),
});

type ForgotPasswordData = z.infer<typeof forgotPasswordSchema>;

function ForgotPasswordForm({ className, ...props }: React.HTMLAttributes<HTMLFormElement>) {
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);

  const form = useForm<ForgotPasswordData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(data: ForgotPasswordData) {
    setIsLoading(true);
    setError(null);
    try {
      await api.post("/auth/forgot-password", { email: data.email })
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  if (success) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-center">
        <h3 className="text-lg font-semibold">Check your email</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          If an account with that email exists, we sent you a password reset link.
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/login">Back to login</Link>
        </Button>
      </div>
    );
  }

  return (
    <form className={cn("space-y-4", className)} onSubmit={form.handleSubmit(onSubmit)} {...props}>
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input id="email" type="email" placeholder="name@example.com" disabled={isLoading} {...form.register("email")} />
        {form.formState.errors.email && <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? "Sending..." : "Send reset link"}
      </Button>
    </form>
  );
}

export { ForgotPasswordForm }
