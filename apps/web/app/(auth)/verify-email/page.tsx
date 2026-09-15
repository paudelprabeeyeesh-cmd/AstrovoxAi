"use client";

export default function VerifyEmailPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-[400px] space-y-6 text-center">
        <div>
          <h1 className="text-2xl font-bold">Verify your email</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            We sent a verification link to your email address. Please check your inbox and click the link to verify your account.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">
            If you don&apos;t see the email, check your spam folder or{" "}
            <button className="font-medium text-primary hover:underline">resend verification email</button>
            .
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          <a href="/login" className="font-medium text-primary hover:underline">
            Back to login
          </a>
        </p>
      </div>
    </div>
  );
}
