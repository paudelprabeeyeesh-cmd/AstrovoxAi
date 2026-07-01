import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Sparkles, Crown, Cpu, Code2, Cloud, Database, Palette, Plug, Boxes, GitBranch, Rocket, Star } from "lucide-react";
import { motion } from "framer-motion";
import { AstroWordmark, AstroMark } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/about")({
  head: () => ({
    meta: [
      { title: "About AstrovoxAI — Credits & Team" },
      {
        name: "description",
        content:
          "AstrovoxAI is a premium AI assistant. Meet the team behind the product: Prabesh Paudel, Dipson Baral, and Susanta Baral.",
      },
      { property: "og:title", content: "About AstrovoxAI" },
      {
        property: "og:description",
        content: "The team and technology behind AstrovoxAI.",
      },
    ],
  }),
  component: AboutPage,
});

const CREATORS = [
  { name: "Dipson Baral", role: "Creator & Engineer" },
  { name: "Susanta Baral", role: "Creator & Engineer" },
];

const PRABESH_ROLES = [
  { icon: Cpu, label: "AI Systems Architect" },
  { icon: Code2, label: "Full-Stack Software Engineer" },
  { icon: Boxes, label: "Python Developer" },
  { icon: Code2, label: "React.js Developer" },
  { icon: Code2, label: "JavaScript & TypeScript Engineer" },
  { icon: Rocket, label: "FastAPI Backend Engineer" },
  { icon: Database, label: "Supabase & PostgreSQL Developer" },
  { icon: Cloud, label: "Cloud & DevOps Enthusiast" },
  { icon: Palette, label: "UI/UX Designer" },
  { icon: Plug, label: "API Integration Specialist" },
  { icon: Boxes, label: "Software Architect" },
  { icon: GitBranch, label: "Open-Source Contributor" },
  { icon: Sparkles, label: "Technology Innovator" },
];

function AboutPage() {
  return (
    <div className="cosmic-bg min-h-screen text-foreground">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <Link to="/">
          <AstroWordmark />
        </Link>
        <Link to="/">
          <Button variant="ghost" className="gap-2 text-foreground/80 hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Home
          </Button>
        </Link>
      </header>

      <main className="mx-auto max-w-5xl px-6 pb-24 pt-12">
        <div className="flex flex-col items-center text-center">
          <AstroMark className="h-14 w-14" />
          <h1
            className="mt-6 text-4xl font-semibold tracking-tight sm:text-5xl"
            style={{ fontFamily: "var(--font-display)" }}
          >
            About AstrovoxAI
          </h1>
          <p className="mt-4 max-w-xl text-base text-muted-foreground">
            AstrovoxAI is a premium conversational AI assistant — built for thinking,
            writing, and coding. Threaded conversations, real-time streaming, and a
            beautiful, distraction-free interface.
          </p>
        </div>

        {/* VIP FOUNDER SPOTLIGHT */}
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="relative mt-16 overflow-hidden rounded-3xl border border-accent/30 bg-gradient-to-br from-primary/20 via-background/60 to-accent/20 p-1 shadow-2xl shadow-primary/30"
        >
          {/* animated aurora glow */}
          <div className="pointer-events-none absolute -top-32 -left-24 h-72 w-72 rounded-full bg-primary/40 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-32 -right-24 h-72 w-72 rounded-full bg-accent/40 blur-3xl" />

          <div className="relative rounded-[calc(1.5rem-4px)] bg-background/70 p-6 backdrop-blur-xl sm:p-10">
            <div className="mb-6 flex items-center justify-center gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-accent">
                <Crown className="h-3.5 w-3.5" />
                VIP · Founder Spotlight
              </span>
            </div>

            <div className="grid gap-10 md:grid-cols-[minmax(0,320px)_1fr] md:items-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.9, ease: "easeOut", delay: 0.1 }}
                className="relative mx-auto w-full max-w-[320px]"
              >
                <div className="absolute -inset-1 rounded-2xl bg-aurora opacity-70 blur-lg" />
                <div className="relative overflow-hidden rounded-2xl border border-accent/30">
                  <img
                    src={prabeshPortrait}
                    alt="Prabesh Paudel — Founder & CEO of AstrovoxAI"
                    width={1024}
                    height={1280}
                    className="h-auto w-full object-cover"
                  />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-background via-background/60 to-transparent p-4">
                    <div className="text-[10px] uppercase tracking-[0.25em] text-accent">
                      Founder · CEO
                    </div>
                  </div>
                </div>
              </motion.div>

              <div className="min-w-0">
                <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">
                  Presenting
                </div>
                <h2
                  className="mt-2 text-balance text-5xl font-bold leading-[1.02] tracking-tight sm:text-6xl md:text-7xl"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  <span className="text-gradient-aurora">Prabesh Paudel</span>
                </h2>
                <div className="mt-4 flex flex-wrap items-center gap-2 text-base text-foreground/90">
                  <span className="rounded-md bg-primary/20 px-2.5 py-1 text-sm font-semibold text-primary-foreground">
                    Founder &amp; CEO
                  </span>
                  <span className="text-muted-foreground">·</span>
                  <span className="font-medium">Astrovox AI</span>
                </div>

                <p className="mt-6 max-w-xl text-sm leading-relaxed text-foreground/80 sm:text-base">
                  Visionary technologist and the architect behind AstrovoxAI. Prabesh leads
                  product, engineering, and design — turning frontier AI into a warm,
                  premium experience anyone can use.
                </p>

                <div className="mt-6 flex flex-wrap gap-2">
                  {PRABESH_ROLES.map(({ icon: Icon, label }) => (
                    <span
                      key={label}
                      className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-card/60 px-3 py-1.5 text-xs text-foreground/85 backdrop-blur-md transition hover:border-accent/50 hover:text-foreground"
                    >
                      <Icon className="h-3 w-3 text-accent" />
                      {label}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.section>

        <section className="mt-16">
          <div className="mb-6 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent" />
            <h2
              className="text-2xl font-semibold tracking-tight"
              style={{ fontFamily: "var(--font-display)" }}
            >
              Team &amp; Credits
            </h2>
          </div>
          <p className="mb-6 text-sm text-muted-foreground">
            AstrovoxAI is also built with:
          </p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {CREATORS.map((c) => (
              <li
                key={c.name}
                className="surface-glass rounded-xl px-5 py-4 text-center"
              >
                <div className="text-base font-medium text-foreground">{c.name}</div>
                <div className="mt-1 text-xs text-muted-foreground">{c.role}</div>
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-16">
          <h2
            className="text-2xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Technology
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            AstrovoxAI streams real-time responses from large language models via a
            secure server-side integration. API keys are stored as encrypted
            environment variables and never exposed to the browser. AstrovoxAI is an
            independent product and is not endorsed by or affiliated with any AI
            provider.
          </p>
        </section>
      </main>
    </div>
  );
}