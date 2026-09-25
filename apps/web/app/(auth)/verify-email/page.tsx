"use client";
import * as React from "react";
import { VerifyEmailForm } from "@/components/auth/verify-email-form";
import Link from "next/link";

export default function VerifyEmailPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-[400px] space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Verify your email</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Enter the verification token sent to your email.
          </p>
        </div>
        <VerifyEmailForm />
        <p className="text-center text-sm text-muted-foreground">
          <Link href="/login" className="font-medium text-primary hover:underline">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}
