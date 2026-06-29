import { createFileRoute } from "@tanstack/react-router";
import { convertToModelMessages, streamText, type UIMessage } from "ai";
import { z } from "zod";
import {
  ASTROVOX_MODELS,
  ASTROVOX_SYSTEM_PROMPT,
  DEFAULT_MODEL,
  createOpenAIProvider,
  type AstrovoxModelId,
} from "@/lib/ai-gateway.server";

const BodySchema = z.object({
  messages: z.array(z.any()),
  model: z.string().optional(),
  conversationId: z.string().uuid().optional(),
});

const allowedModels = new Set<string>(ASTROVOX_MODELS.map((m) => m.id));

export const Route = createFileRoute("/api/chat")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const openaiKey = process.env.OPENAI_API_KEY;
        if (!openaiKey) {
          return new Response(JSON.stringify({ error: "OpenAI API key is not configured on the server." }), {
            status: 500,
            headers: { "content-type": "application/json" },
          });
        }

        // Authenticate
        const authHeader = request.headers.get("authorization") ?? "";
        const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : null;
        if (!token) {
          return new Response(JSON.stringify({ error: "Unauthorized" }), {
            status: 401,
            headers: { "content-type": "application/json" },
          });
        }

        // Verify user via Supabase
        const { createClient } = await import("@supabase/supabase-js");
        const supabase = createClient(
          process.env.SUPABASE_URL!,
          process.env.SUPABASE_PUBLISHABLE_KEY!,
          {
            global: { headers: { Authorization: `Bearer ${token}` } },
            auth: { persistSession: false, autoRefreshToken: false },
          },
        );
        const { data: userRes, error: userErr } = await supabase.auth.getUser(token);
        if (userErr || !userRes.user) {
          return new Response(JSON.stringify({ error: "Unauthorized" }), {
            status: 401,
            headers: { "content-type": "application/json" },
          });
        }
        const userId = userRes.user.id;

        let parsed;
        try {
          parsed = BodySchema.parse(await request.json());
        } catch {
          return new Response(JSON.stringify({ error: "Invalid body" }), {
            status: 400,
            headers: { "content-type": "application/json" },
          });
        }

        const modelId: AstrovoxModelId = allowedModels.has(parsed.model ?? "")
          ? (parsed.model as AstrovoxModelId)
          : DEFAULT_MODEL;

        const provider = createOpenAIProvider(openaiKey);
        const messages = parsed.messages as UIMessage[];

        // Persist the last user message (the new one)
        const lastUser = [...messages].reverse().find((m) => m.role === "user");
        if (parsed.conversationId && lastUser) {
          const text = extractText(lastUser);
          await supabase.from("messages").insert({
            conversation_id: parsed.conversationId,
            user_id: userId,
            role: "user",
            content: text,
            parts: lastUser.parts ?? null,
          });
          await supabase
            .from("conversations")
            .update({ updated_at: new Date().toISOString(), model: modelId })
            .eq("id", parsed.conversationId)
            .eq("user_id", userId);
        }

        try {
          const result = streamText({
            model: provider(modelId),
            system: ASTROVOX_SYSTEM_PROMPT,
            messages: await convertToModelMessages(messages),
            onFinish: async ({ text }) => {
              if (parsed.conversationId && text) {
                await supabase.from("messages").insert({
                  conversation_id: parsed.conversationId,
                  user_id: userId,
                  role: "assistant",
                  content: text,
                  parts: null,
                });
                await supabase
                  .from("conversations")
                  .update({ updated_at: new Date().toISOString() })
                  .eq("id", parsed.conversationId)
                  .eq("user_id", userId);

                // Auto-title if still default
                const { data: convo } = await supabase
                  .from("conversations")
                  .select("title")
                  .eq("id", parsed.conversationId)
                  .eq("user_id", userId)
                  .maybeSingle();
                if (convo && (convo.title === "New chat" || !convo.title)) {
                  const firstUserText = lastUser ? extractText(lastUser) : "";
                  const title = firstUserText.slice(0, 60).trim() || "New chat";
                  await supabase
                    .from("conversations")
                    .update({ title })
                    .eq("id", parsed.conversationId)
                    .eq("user_id", userId);
                }
              }
            },
          });

          return result.toUIMessageStreamResponse();
        } catch (err) {
          const status = (err as { statusCode?: number })?.statusCode ?? 500;
          const message = err instanceof Error ? err.message : "AI gateway error";
          if (status === 429) {
            return new Response(JSON.stringify({ error: "Rate limit reached. Try again shortly." }), {
              status: 429,
              headers: { "content-type": "application/json" },
            });
          }
          if (status === 401) {
            return new Response(
              JSON.stringify({ error: "Invalid OpenAI API key. Please check your server configuration." }),
              { status: 401, headers: { "content-type": "application/json" } },
            );
          }
          if (status === 402 || status === 429) {
            return new Response(
              JSON.stringify({ error: "OpenAI quota exceeded. Please check your plan and billing." }),
              { status, headers: { "content-type": "application/json" } },
            );
          }
          return new Response(JSON.stringify({ error: message }), {
            status: 500,
            headers: { "content-type": "application/json" },
          });
        }
      },
    },
  },
});

function extractText(message: UIMessage): string {
  if (!message.parts) return "";
  return message.parts
    .map((p) => (p && typeof p === "object" && "type" in p && p.type === "text" ? (p as { text: string }).text : ""))
    .join("");
}