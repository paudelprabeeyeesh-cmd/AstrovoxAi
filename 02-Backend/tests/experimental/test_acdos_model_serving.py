"""Tests for the model serving platform."""

from __future__ import annotations

import asyncio
import unittest

from app.acdos.model_serving import (
    Deployment,
    DeploymentManager,
    DeploymentStrategy,
    Model,
    ModelRegistry,
    ModelServer,
    ModelStatus,
    ModelVersion,
    get_deployment_manager,
    get_model_registry,
    get_model_server,
)
from app.acdos.control_plane import ClusterCoordinator, Node


class ModelRegistryTest(unittest.TestCase):
    def setUp(self):
        from app.acdos import model_serving as ms
        ms._GLOBAL_REGISTRY = None

    def test_register_model(self):
        registry = ModelRegistry()
        model = Model(id="m1", name="bert", owner="u1", description="BERT model")
        registry.register(model)
        self.assertEqual(registry.get("m1").id, "m1")

    def test_duplicate_model(self):
        registry = ModelRegistry()
        registry.register(Model(id="m1", name="m1", owner="u1"))
        with self.assertRaises(ValueError):
            registry.register(Model(id="m1", name="m1", owner="u1"))

    def test_version_management(self):
        registry = ModelRegistry()
        model = Model(id="m1", name="bert", owner="u1")
        registry.register(model)
        v1 = ModelVersion(id="v1", model_id="m1", version="1.0.0", artifact_uri="s3://m/1", framework="pytorch")
        registry.add_version("m1", v1)
        self.assertEqual(registry.get("m1").versions["1.0.0"].version, "1.0.0")

    def test_set_current_version(self):
        registry = ModelRegistry()
        model = Model(id="m1", name="bert", owner="u1")
        registry.register(model)
        v1 = ModelVersion(id="v1", model_id="m1", version="1.0.0", artifact_uri="s3://m/1", framework="pytorch")
        v2 = ModelVersion(id="v2", model_id="m1", version="2.0.0", artifact_uri="s3://m/2", framework="pytorch")
        registry.add_version("m1", v1)
        registry.add_version("m1", v2)
        self.assertTrue(registry.set_current("m1", "2.0.0"))
        self.assertEqual(registry.get("m1").current_version, "2.0.0")

    def test_set_default_version(self):
        registry = ModelRegistry()
        model = Model(id="m1", name="bert", owner="u1")
        registry.register(model)
        v1 = ModelVersion(id="v1", model_id="m1", version="1.0.0", artifact_uri="s3://m/1", framework="pytorch")
        registry.add_version("m1", v1)
        self.assertTrue(registry.set_default("m1", "1.0.0"))
        self.assertEqual(registry.get("m1").default_version, "1.0.0")


class DeploymentManagerTest(unittest.TestCase):
    def setUp(self):
        from app.acdos import model_serving as ms
        from app.acdos import control_plane as cp
        ms._GLOBAL_REGISTRY = None
        ms._GLOBAL_DEPLOYMENTS = None
        cp._GLOBAL_COORDINATOR = None
        self.coord = cp.ClusterCoordinator()
        self.coord.add_node(Node(id="n1", address="a", capacity={"cpu": 8.0}))
        self.registry = get_model_registry()
        self.model = Model(id="m1", name="bert", owner="u1")
        self.registry.register(self.model)
        v1 = ModelVersion(id="v1", model_id="m1", version="1.0.0", artifact_uri="s3://m/1", framework="pytorch")
        self.registry.add_version("m1", v1)

    def test_create_deployment(self):
        dm = get_deployment_manager()
        dep = Deployment(id="d1", model_id="m1", version="1.0.0", replicas=3)
        dm.create(dep)
        self.assertEqual(dm.get("d1").replicas, 3)

    def test_recreate_rollout(self):
        dm = get_deployment_manager()
        dep = Deployment(id="d1", model_id="m1", version="1.0.0", strategy=DeploymentStrategy.RECREATE, replicas=2)
        dm.create(dep)
        result = asyncio.run(dm.rollout("d1"))
        self.assertTrue(result["ok"])

    def test_rolling_rollout(self):
        dm = get_deployment_manager()
        dep = Deployment(id="d1", model_id="m1", version="1.0.0", strategy=DeploymentStrategy.ROLLING, replicas=3)
        dm.create(dep)
        result = asyncio.run(dm.rollout("d1"))
        self.assertTrue(result["ok"])

    def test_canary_rollout(self):
        dm = get_deployment_manager()
        dep = Deployment(id="d1", model_id="m1", version="1.0.0", strategy=DeploymentStrategy.CANARY, replicas=10, canary_percentage=0.2)
        dm.create(dep)
        result = asyncio.run(dm.rollout("d1"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["canary_replicas"], 2)

    def test_blue_green_rollout(self):
        dm = get_deployment_manager()
        dep = Deployment(id="d1", model_id="m1", version="1.0.0", strategy=DeploymentStrategy.BLUE_GREEN, replicas=2)
        dm.create(dep)
        result = asyncio.run(dm.rollout("d1"))
        self.assertTrue(result["ok"])

    def test_scale(self):
        dm = get_deployment_manager()
        dep = Deployment(id="d1", model_id="m1", version="1.0.0", replicas=2)
        dm.create(dep)
        self.assertTrue(dm.scale("d1", 5))
        self.assertEqual(dm.get("d1").replicas, 5)

    def test_pause_resume(self):
        dm = get_deployment_manager()
        dep = Deployment(id="d1", model_id="m1", version="1.0.0")
        dm.create(dep)
        self.assertTrue(dm.pause("d1"))
        self.assertEqual(dm.get("d1").status, "paused")
        self.assertTrue(dm.resume("d1"))
        self.assertEqual(dm.get("d1").status, "active")


class ModelServerTest(unittest.TestCase):
    def setUp(self):
        from app.acdos import model_serving as ms
        ms._GLOBAL_REGISTRY = None
        ms._GLOBAL_SERVER = None
        from app.acdos import control_plane as cp
        cp._GLOBAL_COORDINATOR = None
        self.coord = cp.ClusterCoordinator()
        self.coord.add_node(Node(id="n1", address="a", capacity={"cpu": 8.0}))
        self.registry = get_model_registry()
        self.model = Model(id="m1", name="bert", owner="u1")
        self.registry.register(self.model)
        v1 = ModelVersion(id="v1", model_id="m1", version="1.0.0", artifact_uri="s3://m/1", framework="pytorch")
        self.registry.add_version("m1", v1)

    def test_predict(self):
        server = get_model_server()
        result = server.predict("m1", ["input1", "input2"])
        self.assertEqual(result["model_id"], "m1")
        self.assertEqual(len(result["outputs"]), 2)

    def test_predict_with_version(self):
        server = get_model_server()
        result = server.predict("m1", ["x"], version="1.0.0")
        self.assertEqual(result["version"], "1.0.0")

    def test_ab_test(self):
        server = get_model_server()
        test = server.create_ab_test("test1", {"v1": {"weight": 0.5}, "v2": {"weight": 0.5}})
        self.assertEqual(test["name"], "test1")

    def test_batching(self):
        async def run():
            server = get_model_server()
            await server.start_batching(batch_size=2, max_wait_ms=10)
            await server.stop_batching()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()