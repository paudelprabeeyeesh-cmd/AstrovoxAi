import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { ArrowRight, Sparkles, Code2, MessageSquare, Shield, Zap, Github } from "lucide-react";
import { motion } from "framer-motion";
import { AstroWordmark, AstroMark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AstrovoxAI — Premium conversational AI" },
      {
        name: "description",
        content:
          "AstrovoxAI is a premium AI assistant for thinking, writing, and coding. Threaded conversations, real-time streaming, and a beautiful interface.",
      },
      { property: "og:title", content: "AstrovoxAI — Premium conversational AI" },
      {
        property: "og:description",
        content: "Threaded AI conversations with real-time streaming and a beautiful interface.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  return (
    <div className="cosmic-bg min-h-screen text-foreground">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <AstroWordmark />
        <nav className="flex items-center gap-2">
          <Link to="/auth">
            <Button variant="ghost" className="text-foreground/80 hover:text-foreground">
              Sign in
            </Button>
          </Link>
          <Link to="/auth">
            <Button className="bg-aurora text-primary-foreground shadow-lg shadow-primary/20 hover:opacity-90">
              Get started <ArrowRight className="ml-1 h-4 w-4" />
            </Button>
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 pb-24 pt-12 sm:pt-20">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="mx-auto max-w-3xl text-center"
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/40 px-3 py-1 text-xs text-muted-foreground backdrop-blur-md">
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Now in early access · Powered by frontier models
          </span>
          <h1
            className="mt-6 text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Think faster with <span className="text-gradient-aurora">AstrovoxAI</span>
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-balance text-base text-muted-foreground sm:text-lg">
            A premium AI assistant for writing, reasoning, and coding. Real-time streaming, threaded
            memory, and a beautiful conversation-first interface.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link to="/auth">
              <Button
                size="lg"
                className="bg-aurora text-primary-foreground shadow-xl shadow-primary/30 hover:opacity-90"
              >
                Start chatting free <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-md border border-border bg-card/40 px-4 py-2 text-sm text-foreground/80 backdrop-blur-md transition hover:text-foreground"
            >
              <Github className="h-4 w-4" /> Connect GitHub
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          className="mx-auto mt-16 max-w-4xl"
        >
          <div className="surface-glass relative overflow-hidden rounded-3xl p-6 shadow-2xl shadow-primary/10 sm:p-10">
            <div className="absolute -right-20 -top-20 h-60 w-60 rounded-full bg-aurora opacity-20 blur-3xl" />
            <div className="absolute -bottom-24 -left-16 h-60 w-60 rounded-full bg-accent opacity-20 blur-3xl" />
            <div className="relative space-y-4">
              <div className="flex items-center gap-3">
                <AstroMark className="h-7 w-7" />
                <div className="text-sm font-medium text-foreground/80">AstrovoxAI</div>
              </div>
              <p className="text-base leading-relaxed text-foreground/90 sm:text-lg">
                Hey — I'm AstrovoxAI. Ask me to draft, refactor, explain, brainstorm, or plan. I
                stream responses in real time and remember our conversation so we can build on ideas
                together.
              </p>
              <div className="flex flex-wrap gap-2 pt-2">
                {[
                  "Explain quantum entanglement in 3 bullets",
                  "Refactor this function in Python",
                  "Plan a weekend in Tokyo",
                  "Write a cold email for my SaaS",
                ].map((s) => (
                  <span
                    key={s}
                    className="rounded-full border border-border bg-background/40 px-3 py-1 text-xs text-muted-foreground"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        <div className="mx-auto mt-24 grid max-w-5xl gap-5 sm:grid-cols-3">
          {[
            {
              icon: Zap,
              title: "Real-time streaming",
              body: "Tokens appear instantly with stop & regenerate controls.",
            },
            {
              icon: MessageSquare,
              title: "Threaded memory",
              body: "Every conversation is saved, searchable, and yours.",
            },
            {
              icon: Code2,
              title: "Coding-ready",
              body: "Syntax highlighting, copy code, and GitHub-ready architecture.",
            },
            {
              icon: Shield,
              title: "Private by default",
              body: "Row-level security. Your data is scoped to your account.",
            },
            {
              icon: Sparkles,
              title: "Multiple models",
              body: "Switch between flagship models without changing tools.",
            },
            {
              icon: Github,
              title: "GitHub-aware",
              body: "Browse and reason about your repositories (coming soon).",
            },
          ].map(({ icon: Icon, title, body }) => (
            <div
              key={title}
              className="surface-glass rounded-2xl p-5 transition hover:border-accent/40"
            >
              <Icon className="h-5 w-5 text-accent" />
              <h3
                className="mt-3 text-base font-semibold"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {title}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="border-t border-border/60 py-8 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} AstrovoxAI · Built with care
      </footer>
    </div>
  );
}
