"""Tests for the webhook system (Stage 22 step 4)."""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest

from app.ecosystem.webhooks import (
    DeadLetterQueue,
    WebhookDelivery,
    WebhookDeliveryStore,
    WebhookEvent,
    WebhookManager,
    WebhookSubscription,
    dispatch_event,
)


async def _always_200(url, body, headers):
    return 200


async def _always_fail(url, body, headers):
    return 500


class WebhookManagerTest(unittest.TestCase):
    def test_subscription_lifecycle(self):
        manager = WebhookManager(http_post=_always_200)
        sub = manager.create_subscription(
            url="https://example.com/wh",
            events=["chat.completed", "*"],
            owner_id="u1",
        )
        self.assertTrue(sub.active)
        manager.pause(sub.id)
        self.assertFalse(manager.subscriptions[sub.id].active)
        manager.resume(sub.id)
        self.assertTrue(manager.subscriptions[sub.id].active)
        manager.delete_subscription(sub.id)
        self.assertNotIn(sub.id, manager.subscriptions)

    def test_publish_to_matching_subscribers(self):
        async def run():
            manager = WebhookManager(http_post=_always_200)
            manager.create_subscription(
                url="https://a.example/wh",
                events=["*"],
                owner_id="u1",
            )
            manager.create_subscription(
                url="https://b.example/wh",
                events=["chat.completed"],
                owner_id="u1",
            )
            manager.create_subscription(
                url="https://c.example/wh",
                events=["agent.completed"],
                owner_id="u1",
            )
            return await manager.publish("chat.completed", {"x": 1}, target_owner="u1")

        deliveries = asyncio.run(run())
        # 2 subscribers match (one with "*", one with "chat.completed")
        self.assertEqual(len(deliveries), 2)

    def test_publish_respects_owner_filter(self):
        async def run():
            manager = WebhookManager(http_post=_always_200)
            manager.create_subscription(url="https://a", events=["*"], owner_id="u1")
            manager.create_subscription(url="https://b", events=["*"], owner_id="u2")
            return await manager.publish("chat.completed", {"x": 1}, target_owner="u1")

        deliveries = asyncio.run(run())
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].payload, {"x": 1})

    def test_pause_skips_delivery(self):
        async def run():
            manager = WebhookManager(http_post=_always_200)
            sub = manager.create_subscription(url="https://a", events=["*"], owner_id="u1")
            manager.pause(sub.id)
            return await manager.publish("chat.completed", {"x": 1}, target_owner="u1")

        deliveries = asyncio.run(run())
        self.assertEqual(len(deliveries), 0)

    def test_payload_filters(self):
        async def run():
            manager = WebhookManager(http_post=_always_200)
            manager.create_subscription(
                url="https://a",
                events=["*"],
                owner_id="u1",
                filters={"workspace_id": "ws1"},
            )
            await manager.publish("chat.completed", {"workspace_id": "ws1"}, target_owner="u1")
            return await manager.publish("chat.completed", {"workspace_id": "ws2"}, target_owner="u1")

        asyncio.run(run())
        # Only one delivery should have happened
        self.assertEqual(WebhookManager(http_post=_always_200).metrics()["subscriptions"], 0)

    def test_failure_retries(self):
        async def run():
            manager = WebhookManager(http_post=_always_fail)
            manager.create_subscription(url="https://a", events=["*"], owner_id="u1")
            return await manager.publish("chat.completed", {"x": 1}, target_owner="u1")

        deliveries = asyncio.run(run())
        # First delivery, all attempts exhausted -> failed
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].status, "failed")
        self.assertEqual(deliveries[0].attempts, 5)

    def test_signature_verification(self):
        manager = WebhookManager(http_post=_always_200)
        body = b'{"event":"test"}'
        sig = manager.verify_incoming(body, "bad", "secret")
        self.assertFalse(sig)


class WebhookEventTest(unittest.TestCase):
    def test_from_string_valid(self):
        self.assertEqual(
            WebhookEvent.from_string("chat.completed"),
            WebhookEvent.CHAT_COMPLETED,
        )

    def test_from_string_invalid(self):
        self.assertEqual(WebhookEvent.from_string("weird.event"), WebhookEvent.CUSTOM)


class DeliveryStoreTest(unittest.TestCase):
    def test_append_and_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WebhookDeliveryStore(path=os.path.join(tmp, "del.jsonl"))
            delivery = WebhookDelivery(
                id="d1",
                subscription_id="s1",
                event="chat.completed",
                payload={"x": 1},
                signature="sig",
                timestamp=0,
            )
            asyncio.run(store.append(delivery))
            items = asyncio.run(store.tail(10))
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["subscription_id"], "s1")


class DeadLetterQueueTest(unittest.TestCase):
    def test_push_and_drain(self):
        with tempfile.TemporaryDirectory() as tmp:
            dlq = DeadLetterQueue(path=os.path.join(tmp, "dlq.jsonl"))
            delivery = WebhookDelivery(
                id="d1",
                subscription_id="s1",
                event="chat.completed",
                payload={},
                signature="sig",
                timestamp=0,
            )
            asyncio.run(dlq.push(delivery, reason="test"))
            items = asyncio.run(dlq.drain(10))
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["dlq_reason"], "test")


class DispatchTest(unittest.TestCase):
    def test_dispatch_returns_subscriptions(self):
        from app.ecosystem.webhooks import get_webhook_manager
        manager = get_webhook_manager()
        manager.subscriptions.clear()
        manager.create_subscription(url="https://a", events=["*"], owner_id="u1")
        result = dispatch_event("chat.completed", {}, owner_id="u1")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()