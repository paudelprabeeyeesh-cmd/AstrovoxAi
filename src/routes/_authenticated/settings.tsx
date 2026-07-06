import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useServerFn } from "@tanstack/react-start";
import { ArrowLeft, Github, Mail, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AstroWordmark } from "@/components/brand/Logo";
import { getProfile, updateProfile } from "@/lib/conversations.functions";

export const Route = createFileRoute("/_authenticated/settings")({
  component: SettingsPage,
});

function SettingsPage() {
  const qc = useQueryClient();
  const getFn = useServerFn(getProfile);
  const updateFn = useServerFn(updateProfile);
  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: () => getFn(),
  });
  const [name, setName] = useState("");
  const [avatar, setAvatar] = useState("");

  useEffect(() => {
    if (profile) {
      setName(profile.display_name ?? "");
      setAvatar(profile.avatar_url ?? "");
    }
  }, [profile]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateFn({ data: { display_name: name, avatar_url: avatar } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile saved");
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Save failed"),
  });

  return (
    <div className="cosmic-bg min-h-screen px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <div className="mb-6 flex items-center justify-between">
          <Link to="/chat" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back to chat
          </Link>
          <AstroWordmark className="scale-90" />
        </div>

        <div className="surface-glass rounded-2xl p-6">
          <h1
            className="text-xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Profile
          </h1>
          {isLoading ? (
            <div className="mt-6 flex justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : (
            <div className="mt-5 space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="name">Display name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  maxLength={80}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="avatar">Avatar URL</Label>
                <Input
                  id="avatar"
                  value={avatar}
                  onChange={(e) => setAvatar(e.target.value)}
                  placeholder="https://…"
                />
              </div>
              <Button
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
                className="bg-aurora text-primary-foreground hover:opacity-90"
              >
                {saveMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Save changes
              </Button>
            </div>
          )}
        </div>

        <div className="surface-glass mt-6 rounded-2xl p-6">
          <h2
            className="text-lg font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Integrations
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Connect external services to unlock more capabilities in AstrovoxAI.
          </p>
          <div className="mt-4 space-y-3">
            <IntegrationRow
              icon={<Github className="h-5 w-5" />}
              title="GitHub"
              body="Browse repositories and reason about your code (coming soon — requires a GitHub OAuth app)."
              cta="Coming soon"
            />
            <IntegrationRow
              icon={<Mail className="h-5 w-5" />}
              title="Resend (email)"
              body="Send AstrovoxAI summaries by email (requires RESEND_API_KEY)."
              cta="Coming soon"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function IntegrationRow({
  icon,
  title,
  body,
  cta,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  cta: string;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-border bg-card/40 p-4">
      <div className="flex items-start gap-3">
        <div className="rounded-lg bg-background p-2 text-foreground/80">{icon}</div>
        <div>
          <div className="font-medium">{title}</div>
          <div className="text-sm text-muted-foreground">{body}</div>
        </div>
      </div>
      <Button variant="outline" size="sm" disabled>
        {cta}
      </Button>
    </div>
  );
}