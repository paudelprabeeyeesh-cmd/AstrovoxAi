# @astrovoxai/sdk

Official JavaScript/TypeScript SDK for the AstrovoxAI Developer Platform.

## Install

```bash
npm install @astrovoxai/sdk
```

## Quick start

```ts
import { AstrovoxClient } from "@astrovoxai/sdk";

const client = new AstrovoxClient({
  baseUrl: "https://api.astrovox.ai",
  apiKey: process.env.ASTROVOX_KEY!,
  apiSecret: process.env.ASTROVOX_SECRET!,
});

const reply = await client.chat([
  { role: "user", content: "Hello, AstrovoxAI!" },
]);

const plugins = await client.listPlugins();
await client.installPlugin("github");
await client.invokePlugin("github", "list_repos", ["astrovox-ai"]);
```

## Webhook signatures

```ts
import { verifyPayload } from "@astrovoxai/sdk";

app.post("/webhook", (req, res) => {
  const sig = req.headers["x-astrovox-signature"] as string;
  const ok = verifyPayload(req.rawBody, sig, process.env.WEBHOOK_SECRET!);
  if (!ok) return res.status(401).send("invalid");
  // handle event
  res.status(200).end();
});
```