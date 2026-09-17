"use client";
import { LoginForm } from "@/components/auth/login-form";
import Link from "next/link";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-[400px] space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold">Sign in to AstrovoxAI</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Welcome back! Please enter your details.
          </p>
        </div>
        <LoginForm onSuccess={() => { window.location.href = "/dashboard"; }} />
        <p className="text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-primary hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
