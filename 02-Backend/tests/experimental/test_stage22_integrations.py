"""Tests for third-party integrations (Stage 22 step 5)."""

from __future__ import annotations

import unittest

from app.ecosystem.integrations import (
    IntegrationClient,
    IntegrationConnection,
    IntegrationProvider,
    IntegrationRegistry,
    IntegrationStore,
    build_pkce_pair,
    sign_state,
    verify_state,
)


class IntegrationRegistryTest(unittest.TestCase):
    def test_catalog_lists_all_providers(self):
        registry = IntegrationRegistry()
        items = registry.list()
        ids = {i["provider"] for i in items}
        self.assertIn("github", ids)
        self.assertIn("slack", ids)
        self.assertIn("notion", ids)
        self.assertIn("jira", ids)
        self.assertIn("gdrive", ids)
        self.assertIn("dropbox", ids)
        self.assertIn("onedrive", ids)
        self.assertIn("discord", ids)
        self.assertIn("gitlab", ids)
        self.assertIn("trello", ids)

    def test_get(self):
        registry = IntegrationRegistry()
        github = registry.get(IntegrationProvider.GITHUB)
        self.assertIsNotNone(github)
        self.assertEqual(github.auth_type, "oauth2")

    def test_by_category(self):
        registry = IntegrationRegistry()
        storage = registry.by_category("storage")
        self.assertGreater(len(storage), 0)
        for item in storage:
            self.assertEqual(item["category"], "storage")


class IntegrationStoreTest(unittest.TestCase):
    def test_add_get(self):
        store = IntegrationStore()
        conn = IntegrationConnection(
            id="int-1", provider=IntegrationProvider.GITHUB,
            owner_id="u1", label="test",
        )
        store.add(conn)
        self.assertIs(store.get("int-1"), conn)

    def test_by_owner(self):
        store = IntegrationStore()
        store.add(IntegrationConnection(id="a", provider=IntegrationProvider.SLACK, owner_id="u1", label="a"))
        store.add(IntegrationConnection(id="b", provider=IntegrationProvider.SLACK, owner_id="u2", label="b"))
        self.assertEqual(len(store.by_owner("u1")), 1)
        self.assertEqual(len(store.by_owner("u2")), 1)

    def test_by_provider(self):
        store = IntegrationStore()
        store.add(IntegrationConnection(id="a", provider=IntegrationProvider.SLACK, owner_id="u1", label="a"))
        store.add(IntegrationConnection(id="b", provider=IntegrationProvider.GITHUB, owner_id="u1", label="b"))
        slacks = store.by_provider(IntegrationProvider.SLACK)
        self.assertEqual(len(slacks), 1)

    def test_remove(self):
        store = IntegrationStore()
        conn = IntegrationConnection(id="a", provider=IntegrationProvider.SLACK, owner_id="u1", label="a")
        store.add(conn)
        self.assertIs(store.remove("a"), conn)
        self.assertIsNone(store.get("a"))


class IntegrationClientTest(unittest.TestCase):
    def setUp(self):
        self.store = IntegrationStore()
        self.conn = IntegrationConnection(
            id="int-1",
            provider=IntegrationProvider.GITHUB,
            owner_id="u1",
            label="test",
            access_token="x",
        )
        self.store.add(self.conn)
        self.client = IntegrationClient(self.store)

    def test_github_actions(self):
        out = self.client.github_list_repos(self.conn.id, owner="astrovox-ai")
        self.assertTrue(out["ok"])
        issue = self.client.github_create_issue(self.conn.id, "org/repo", "Bug", "details")
        self.assertTrue(issue["ok"])

    def test_github_missing_connection(self):
        with self.assertRaises(ValueError):
            self.client.github_list_repos("missing")

    def test_storage_actions(self):
        drive = IntegrationConnection(
            id="int-2",
            provider=IntegrationProvider.GOOGLE_DRIVE,
            owner_id="u1",
            label="drive",
        )
        self.store.add(drive)
        out = self.client.storage_list_files(drive.id, "root")
        self.assertTrue(out["ok"])
        upload = self.client.storage_upload(drive.id, "x.txt", b"hello", folder_id="root")
        self.assertTrue(upload["ok"])

    def test_slack_post(self):
        slack = IntegrationConnection(
            id="int-slack",
            provider=IntegrationProvider.SLACK,
            owner_id="u1",
            label="slack",
        )
        self.store.add(slack)
        out = self.client.slack_post_message(slack.id, "#general", "hello")
        self.assertTrue(out["ok"])

    def test_discord_no_webhook(self):
        discord = IntegrationConnection(
            id="int-discord",
            provider=IntegrationProvider.DISCORD,
            owner_id="u1",
            label="discord",
        )
        self.store.add(discord)
        out = self.client.discord_post_message(discord.id, "#channel", "hi")
        self.assertFalse(out["ok"])
        self.assertIn("webhook_url", out["error"])

    def test_jira_create(self):
        jira = IntegrationConnection(
            id="int-jira", provider=IntegrationProvider.JIRA, owner_id="u1", label="jira"
        )
        self.store.add(jira)
        out = self.client.jira_create_issue(jira.id, "PROJ", "task", "desc")
        self.assertTrue(out["ok"])
        self.assertIn("id", out)

    def test_trello_create(self):
        trello = IntegrationConnection(
            id="int-trello", provider=IntegrationProvider.TRELLO, owner_id="u1", label="trello"
        )
        self.store.add(trello)
        out = self.client.trello_create_card(trello.id, "board", "todo", "title")
        self.assertTrue(out["ok"])

    def test_notion_list(self):
        notion = IntegrationConnection(
            id="int-notion", provider=IntegrationProvider.NOTION, owner_id="u1", label="notion"
        )
        self.store.add(notion)
        out = self.client.notion_list_pages(notion.id)
        self.assertTrue(out["ok"])


class PkceTest(unittest.TestCase):
    def test_pair_unique(self):
        v1, c1 = build_pkce_pair()
        v2, c2 = build_pkce_pair()
        self.assertNotEqual(v1, v2)
        self.assertNotEqual(c1, c2)
        self.assertGreater(len(v1), 40)


class StateSigningTest(unittest.TestCase):
    def test_roundtrip(self):
        secret = "s"
        payload = {"a": 1}
        token = sign_state(payload, secret)
        self.assertEqual(verify_state(token, secret), payload)

    def test_tamper(self):
        secret = "s"
        token = sign_state({"a": 1}, secret)
        self.assertIsNone(verify_state(token + "tamper", secret))


if __name__ == "__main__":
    unittest.main()