import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Sparkles } from "lucide-react";
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
  { name: "Prabesh Paudel", role: "Creator & Engineer" },
  { name: "Dipson Baral", role: "Creator & Engineer" },
  { name: "Susanta Baral", role: "Creator & Engineer" },
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

      <main className="mx-auto max-w-3xl px-6 pb-24 pt-12">
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

        <section className="mt-16">
          <div className="mb-6 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-accent" />
            <h2
              className="text-2xl font-semibold tracking-tight"
              style={{ fontFamily: "var(--font-display)" }}
            >
              Credits
            </h2>
          </div>
          <p className="mb-6 text-sm text-muted-foreground">
            This project was created and developed by:
          </p>
          <ul className="grid gap-3 sm:grid-cols-3">
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