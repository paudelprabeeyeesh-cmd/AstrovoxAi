import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Brain, Zap, Shield, ArrowRight, Sparkles, MessageSquare, Users } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col">
      <section className="relative overflow-hidden py-20 lg:py-32">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-background to-background" />
        <div className="relative mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <div className="inline-flex items-center rounded-full border border-border bg-muted px-3 py-1 text-sm text-muted-foreground mb-6">
              <Sparkles className="mr-2 h-4 w-4" />
              Powered by advanced AI
            </div>
            <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
              AstrovoxAI
            </h1>
            <p className="mt-6 text-lg leading-8 text-muted-foreground">
              The AI-powered platform that remembers. Chat, learn, and build with an intelligent assistant that never forgets your context and preferences.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Button asChild size="lg">
                <Link href="/register">Get Started <ArrowRight className="ml-2 h-4 w-4" /></Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href="/login">Sign In</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight">Everything you need to build smarter</h2>
            <p className="mt-4 text-lg text-muted-foreground">
              AstrovoxAI combines cutting-edge AI with persistent memory to help you work more efficiently than ever before.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-2xl grid-cols-1 gap-8 sm:mt-20 lg:max-w-none lg:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <Brain className="h-10 w-10 text-primary" />
              <h3 className="mt-4 text-lg font-semibold">Persistent Memory</h3>
              <p className="mt-2 text-muted-foreground">
                AstrovoxAI remembers your conversations, preferences, and context across all sessions.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <Zap className="h-10 w-10 text-primary" />
              <h3 className="mt-4 text-lg font-semibold">Lightning Fast</h3>
              <p className="mt-2 text-muted-foreground">
                Optimized streaming responses powered by the latest AI models with minimal latency.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <Shield className="h-10 w-10 text-primary" />
              <h3 className="mt-4 text-lg font-semibold">Privacy First</h3>
              <p className="mt-2 text-muted-foreground">
                Your data is encrypted and never shared with third parties. You own your data.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-border bg-muted/50 py-20">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight">How it works</h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Get started in minutes with our simple onboarding process.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-2xl grid-cols-1 gap-8 sm:mt-20 lg:max-w-none lg:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">1</div>
              <h3 className="mt-4 text-lg font-semibold">Create Account</h3>
              <p className="mt-2 text-muted-foreground">
                Sign up in seconds with your email or social accounts. No credit card required.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">2</div>
              <h3 className="mt-4 text-lg font-semibold">Start Chatting</h3>
              <p className="mt-2 text-muted-foreground">
                Begin conversations with your AI assistant. It learns and adapts to your needs.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground font-bold">3</div>
              <h3 className="mt-4 text-lg font-semibold">Build & Grow</h3>
              <p className="mt-2 text-muted-foreground">
                Use persistent memory to build complex projects and maintain context over time.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight">Trusted by teams worldwide</h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Join thousands of users who rely on AstrovoxAI every day.
            </p>
          </div>
          <div className="mx-auto mt-16 grid max-w-2xl grid-cols-1 gap-8 sm:mt-20 lg:max-w-none lg:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <MessageSquare className="h-10 w-10 text-primary" />
              <h3 className="mt-4 text-lg font-semibold">Smart Conversations</h3>
              <p className="mt-2 text-muted-foreground">
                Natural language understanding that feels human-like and context-aware.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <Users className="h-10 w-10 text-primary" />
              <h3 className="mt-4 text-lg font-semibold">Team Collaboration</h3>
              <p className="mt-2 text-muted-foreground">
                Share conversations and memories with your team to boost productivity.
              </p>
            </div>
            <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
              <Brain className="h-10 w-10 text-primary" />
              <h3 className="mt-4 text-lg font-semibold">Intelligent Memory</h3>
              <p className="mt-2 text-muted-foreground">
                Advanced memory systems that organize and recall information intelligently.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-border bg-muted/50 py-20">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="text-3xl font-bold tracking-tight">Ready to get started?</h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Join AstrovoxAI today and experience the future of AI-powered productivity.
            </p>
            <div className="mt-10 flex items-center justify-center gap-4">
              <Button asChild size="lg">
                <Link href="/register">Create free account <ArrowRight className="ml-2 h-4 w-4" /></Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href="/login">Sign In</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
