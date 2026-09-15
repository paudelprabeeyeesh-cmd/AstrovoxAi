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

const resetPasswordSchema = z.object({
  password: z.string().min(8, "Password must be at least 8 characters"),
  confirmPassword: z.string().min(8, "Password must be at least 8 characters"),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords do not match",
  path: ["confirmPassword"],
});

type ResetPasswordData = z.infer<typeof resetPasswordSchema>;

interface ResetPasswordFormProps extends React.HTMLAttributes<HTMLFormElement> {
  token?: string;
}

function ResetPasswordForm({ className, token, ...props }: ResetPasswordFormProps) {
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [success, setSuccess] = React.useState(false);

  const form = useForm<ResetPasswordData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  async function onSubmit(data: ResetPasswordData) {
    setIsLoading(true);
    setError(null);
    try {
      await api.post("/auth/reset-password", { token, new_password: data.password })
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
        <h3 className="text-lg font-semibold">Password reset successful</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          Your password has been updated. You can now sign in with your new password.
        </p>
        <Button className="mt-4" asChild>
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <form className={cn("space-y-4", className)} onSubmit={form.handleSubmit(onSubmit)} {...props}>
      <div className="space-y-2">
        <Label htmlFor="password">New Password</Label>
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
        {isLoading ? "Resetting..." : "Reset password"}
      </Button>
    </form>
  );
}

export { ResetPasswordForm }
