import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable/index";
import { AstroWordmark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in · AstrovoxAI" },
      { name: "description", content: "Sign in or create your AstrovoxAI account." },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    void supabase.auth.getSession().then(({ data }) => {
      if (mounted && data.session) {
        void navigate({ to: "/chat" });
      }
    });
    return () => {
      mounted = false;
    };
  }, [navigate]);

  async function handleEmail(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Email and password are required");
      return;
    }
    setLoading(true);
    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: window.location.origin,
            data: { full_name: name || email.split("@")[0] },
          },
        });
        if (error) throw error;
        toast.success("Welcome to AstrovoxAI!");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        toast.success("Welcome back");
      }
      void navigate({ to: "/chat" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Authentication failed";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setGoogleLoading(true);
    try {
      const result = await lovable.auth.signInWithOAuth("google", {
        redirect_uri: window.location.origin,
      });
      if (result.error) {
        toast.error(result.error.message ?? "Google sign-in failed");
        return;
      }
      if (result.redirected) return;
      void navigate({ to: "/chat" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Google sign-in failed";
      toast.error(message);
    } finally {
      setGoogleLoading(false);
    }
  }

  return (
    <div className="cosmic-bg flex min-h-screen items-center justify-center px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Link to="/" className="mb-8 flex justify-center">
          <AstroWordmark />
        </Link>
        <div className="surface-glass rounded-2xl p-8 shadow-2xl shadow-primary/10">
          <h1
            className="text-2xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {mode === "signin" ? "Welcome back" : "Create your account"}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {mode === "signin"
              ? "Sign in to continue your conversations."
              : "Start chatting with AstrovoxAI in seconds."}
          </p>

          <Button
            type="button"
            variant="outline"
            className="mt-6 w-full border-border bg-card/60 text-foreground hover:bg-card"
            onClick={handleGoogle}
            disabled={googleLoading}
          >
            {googleLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <GoogleIcon className="mr-2 h-4 w-4" />
            )}
            Continue with Google
          </Button>

          <div className="my-5 flex items-center gap-3 text-xs text-muted-foreground">
            <div className="h-px flex-1 bg-border" />
            or with email
            <div className="h-px flex-1 bg-border" />
          </div>

          <form onSubmit={handleEmail} className="space-y-3">
            {mode === "signup" && (
              <div className="space-y-1.5">
                <Label htmlFor="name">Display name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Stella"
                  autoComplete="name"
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@galaxy.com"
                autoComplete="email"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
                minLength={6}
                required
              />
            </div>
            <Button
              type="submit"
              disabled={loading}
              className="mt-2 w-full bg-aurora text-primary-foreground shadow-lg shadow-primary/20 hover:opacity-90"
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {mode === "signin" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-muted-foreground">
            {mode === "signin" ? "New here?" : "Already have an account?"}{" "}
            <button
              type="button"
              onClick={() => setMode((m) => (m === "signin" ? "signup" : "signin"))}
              className="font-medium text-accent hover:underline"
            >
              {mode === "signin" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </div>
      </motion.div>
    </div>
  );
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M12 11.5v3.13h4.42c-.18 1.16-1.34 3.4-4.42 3.4-2.66 0-4.83-2.2-4.83-4.92S9.34 8.18 12 8.18c1.51 0 2.53.65 3.11 1.2l2.12-2.04C15.94 5.99 14.13 5.2 12 5.2 7.97 5.2 4.7 8.46 4.7 12.5S7.97 19.8 12 19.8c6.04 0 7.31-4.24 7.31-7.18 0-.48-.05-.85-.12-1.12H12Z"
      />
      <path
        fill="#34A853"
        d="M12 19.8c2.16 0 3.97-.71 5.29-1.94l-2.59-2.01c-.71.49-1.65.83-2.7.83-2.07 0-3.83-1.39-4.46-3.27H4.83v2.05A7.3 7.3 0 0 0 12 19.8Z"
      />
      <path
        fill="#FBBC05"
        d="M7.54 13.41a4.42 4.42 0 0 1 0-2.82V8.54H4.83a7.3 7.3 0 0 0 0 6.92l2.71-2.05Z"
      />
      <path
        fill="#4285F4"
        d="M12 8.18c1.17 0 2.21.4 3.04 1.2l2.27-2.27C15.94 5.99 14.13 5.2 12 5.2A7.3 7.3 0 0 0 4.83 8.54l2.71 2.05C8.17 9.57 9.93 8.18 12 8.18Z"
      />
    </svg>
  );
}