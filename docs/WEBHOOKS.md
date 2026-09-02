# Webhook Documentation

The AstrovoxAI webhook platform supports both **incoming** and **outgoing**
webhooks, providing reliable event delivery with retries, dead-letter
queueing, and signature verification.

## Subscribing

```
POST /ecosystem/webhooks/subscriptions
{
  "url": "https://example.com/hooks/astrovox",
  "events": ["chat.completed", "agent.completed"],
  "filters": {"workspace_id": "ws_123"}
}
```

The response includes a `secret` used to verify signatures. Save it — it is
only shown once.

## Event Envelope

Outgoing webhooks POST a JSON body with the following shape:

```json
{
  "id": "evt_5f0e",
  "event": "chat.completed",
  "created_at": 1735849212,
  "data": { "...": "..." }
}
```

## Headers

| Header | Description |
|--------|-------------|
| `X-Astrovox-Signature` | HMAC-SHA256 signature (`t=...,v1=...`) |
| `X-Astrovox-Timestamp` | Unix timestamp of the delivery |
| `X-Astrovox-Event` | Event name |
| `X-Astrovox-Delivery` | Delivery id |

## Verifying Signatures

```python
from astrovoxai import AstrovoxClient

ok = AstrovoxClient.verify_payload(raw_body, signature, secret)
```

The signature format is `t=<unix>,v1=<hex>` where the HMAC is computed over
`f"{t}." + body`. Timestamps older than 5 minutes are rejected by default.

## Retries & DLQ

Failed deliveries are retried with exponential backoff (max 5 attempts).
Permanent failures land in the dead-letter queue:

```
GET /ecosystem/webhooks/dlq
GET /ecosystem/webhooks/deliveries
```

## Incoming Webhooks

You can verify an incoming webhook using the same signature scheme by
calling `POST /ecosystem/webhooks/verify` with the body, signature, and
secret.

## Available Events

See `GET /ecosystem/webhooks/events` for the canonical list.

## Best Practices

1. Respond to deliveries with HTTP 2xx as quickly as possible.
2. Process events asynchronously to keep your endpoint responsive.
3. Use the `filters` field to narrow the events you receive.
4. Rotate secrets on a regular cadence via revoke + resubscribe.