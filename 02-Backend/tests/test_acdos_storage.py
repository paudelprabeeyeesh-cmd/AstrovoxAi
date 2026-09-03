"""Tests for the ACDOS storage platform."""

from __future__ import annotations

import asyncio
import unittest

from app.acdos.storage import (
    BackupJob,
    Bucket,
    ConsistencyLevel,
    ConsistencyVerifier,
    ObjectStore,
    ReplicationFactor,
    Snapshot,
    StorageObject,
    StorageTier,
    get_object_store,
    get_consistency_verifier,
)


class ObjectStoreTest(unittest.TestCase):
    def setUp(self):
        from app.acdos import storage as st
        st._GLOBAL_STORE = None

    def test_bucket_lifecycle(self):
        store = get_object_store()
        bucket = Bucket(name="test-bucket", owner="u1")
        store.create_bucket(bucket)
        fetched = store.get_bucket("test-bucket")
        self.assertEqual(fetched.name, "test-bucket")
        self.assertEqual(fetched.owner, "u1")
        store.delete_bucket("test-bucket")
        self.assertIsNone(store.get_bucket("test-bucket"))

    def test_object_put_get(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="b", owner="u1"))
        obj = store.put("b", "key1", b"hello world", content_type="text/plain")
        self.assertEqual(obj.size, 11)
        self.assertEqual(obj.content_type, "text/plain")
        fetched = store.get("b", "key1")
        self.assertEqual(fetched.size, 11)

    def test_versioning(self):
        store = get_object_store()
        b = Bucket(name="v", owner="u1", versioning=True)
        store.create_bucket(b)
        store.put("v", "k", b"v1")
        obj1 = store.get("v", "k")
        store.put("v", "k", b"v2")
        obj2 = store.get("v", "k")
        self.assertEqual(obj2.version, 2)

    def test_delete(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="d", owner="u1"))
        store.put("d", "k", b"x")
        self.assertTrue(store.delete("d", "k"))
        self.assertIsNone(store.get("d", "k"))

    def test_list_with_prefix(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="p", owner="u1"))
        store.put("p", "a/1", b"1")
        store.put("p", "a/2", b"2")
        store.put("p", "b/1", b"3")
        items = store.list("p", "a/")
        self.assertEqual(len(items), 2)

    def test_snapshot(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="s", owner="u1"))
        store.put("s", "k1", b"data1")
        store.put("s", "k2", b"data2")
        snap = store.create_snapshot("s", "snap1")
        self.assertEqual(snap.size, len(b"data1") + len(b"data2"))
        self.assertEqual(len(snap.objects), 2)

    def test_snapshot_list(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="s2", owner="u1"))
        store.create_snapshot("s2", "snap1")
        snaps = store.list_snapshots("s2")
        self.assertEqual(len(snaps), 1)

    def test_backup(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="bk", owner="u1"))
        job = store.backup("bk", "s3://backup")
        self.assertIsNotNone(job.id)

    async def test_backup_run(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="br", owner="u1"))
        job = store.backup("br", "s3://backup")
        result = await store.run_backup(job.id)
        self.assertEqual(result.status, "completed")

    def test_consistency_verifier(self):
        store = get_object_store()
        verifier = ConsistencyVerifier(store)
        store.create_bucket(Bucket(name="cv", owner="u1"))
        store.put("cv", "k", b"test")
        res = verifier.verify_object("cv", "k")
        self.assertTrue(res["ok"])
        self.assertTrue(res["checksum"].startswith(res["etag"]))

    def test_stats(self):
        store = get_object_store()
        store.create_bucket(Bucket(name="st", owner="u1"))
        store.put("st", "k", b"x" * 100)
        stats = store.stats()
        self.assertEqual(stats["objects"], 1)
        self.assertEqual(stats["total_size"], 100)


class BucketTest(unittest.TestCase):
    def test_cors_and_lifecycle(self):
        bucket = Bucket(
            name="test",
            owner="u1",
            cors=[{"origin": "*", "methods": ["GET"]}],
            lifecycle_rules=[{"id": "expire", "days": 30}],
        )
        self.assertEqual(len(bucket.cors), 1)
        self.assertEqual(len(bucket.lifecycle_rules), 1)


class ReplicationTest(unittest.TestCase):
    def test_replication_factor(self):
        from app.acdos.storage import StorageObject
        obj = StorageObject(
            id="o1", bucket="b", key="k",
            size=100, content_type="text/plain",
            replication=2,
        )
        self.assertEqual(obj.replication, 2)


if __name__ == "__main__":
    unittest.main()