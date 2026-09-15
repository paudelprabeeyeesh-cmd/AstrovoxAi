"use client";
import * as React from "react";
import { useSearchParams } from "next/navigation";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-[400px] space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Reset your password</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Choose a strong new password for your account.
          </p>
        </div>
        <ResetPasswordForm token={token || undefined} />
      </div>
    </div>
  );
}
