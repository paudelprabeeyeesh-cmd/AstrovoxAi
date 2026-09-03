"""Tests for the ACDOS distributed control plane."""

from __future__ import annotations

import unittest

from app.acdos.control_plane import (
    ClusterCoordinator,
    LeaderElector,
    Node,
    NodeState,
    Zone,
    ZoneState,
)


class LeaderElectorTest(unittest.TestCase):
    def test_election(self):
        elector = LeaderElector(ttl=10.0)
        self.assertTrue(elector.try_become_leader("a"))
        self.assertFalse(elector.try_become_leader("b"))
        self.assertEqual(elector.leader(), "a")
        elector.step_down()
        self.assertTrue(elector.try_become_leader("b"))

    def test_renew(self):
        elector = LeaderElector(ttl=10.0)
        elector.try_become_leader("a")
        self.assertTrue(elector.renew())


class ClusterCoordinatorTest(unittest.TestCase):
    def test_add_and_heartbeat(self):
        coord = ClusterCoordinator()
        node = coord.add_node(Node(id="", address="10.0.0.1", capacity={"cpu": 8.0}))
        self.assertTrue(coord.heartbeat(node.id))
        self.assertEqual(len(coord.list_nodes(only_healthy=True)), 1)

    def test_remove_node(self):
        coord = ClusterCoordinator()
        node = coord.add_node(Node(id="", address="10.0.0.1"))
        coord.remove_node(node.id)
        self.assertEqual(len(coord.list_nodes()), 0)

    def test_detect_dead(self):
        coord = ClusterCoordinator()
        node = coord.add_node(Node(id="", address="10.0.0.1"))
        node.last_heartbeat = 0
        dead = coord.detect_dead()
        self.assertIn(node.id, dead)

    def test_zones(self):
        coord = ClusterCoordinator()
        coord.add_node(Node(id="", address="a", zone="z1"))
        coord.add_node(Node(id="", address="b", zone="z1"))
        coord.set_zone_state("z1", ZoneState.READ_ONLY)
        self.assertEqual(coord.zone("z1").state, ZoneState.READ_ONLY)

    def test_service_registry(self):
        coord = ClusterCoordinator()
        node = coord.add_node(Node(id="", address="a"))
        coord.register_service("chat", node.id)
        self.assertIn(node.id, coord.discover("chat"))

    def test_leader_election(self):
        coord = ClusterCoordinator()
        self.assertTrue(coord.try_become_leader("a"))
        self.assertEqual(coord.leader(), "a")

    def test_config_distribution(self):
        coord = ClusterCoordinator()
        v1 = coord.set_config("feature_x", True)
        self.assertEqual(coord.get_config("feature_x"), True)
        v2 = coord.set_config("feature_x", False)
        self.assertEqual(v2, v1 + 1)

    def test_schedule(self):
        coord = ClusterCoordinator()
        coord.add_node(Node(id="n1", address="a", capacity={"cpu": 4.0}))
        coord.add_node(Node(id="n2", address="b", capacity={"cpu": 8.0}))
        picked = coord.schedule({"cpu": 1.0})
        self.assertIsNotNone(picked)

    def test_schedule_with_zone_filter(self):
        coord = ClusterCoordinator()
        coord.add_node(Node(id="n1", address="a", zone="z1"))
        coord.add_node(Node(id="n2", address="b", zone="z2"))
        picked = coord.schedule({"cpu": 1.0}, zone="z2")
        self.assertEqual(picked.zone, "z2")

    def test_allocate_and_release(self):
        coord = ClusterCoordinator()
        node = coord.add_node(Node(id="n1", address="a", capacity={"cpu": 4.0}))
        self.assertTrue(coord.allocate(node.id, {"cpu": 2.0}))
        self.assertEqual(node.used["cpu"], 2.0)
        self.assertFalse(coord.allocate(node.id, {"cpu": 3.0}))
        coord.release(node.id, {"cpu": 1.0})
        self.assertEqual(node.used["cpu"], 1.0)

    def test_upgrade(self):
        coord = ClusterCoordinator()
        upgrade = coord.start_upgrade("2.0.0")
        self.assertEqual(upgrade["status"], "in_progress")
        self.assertTrue(coord.complete_upgrade(upgrade["id"]))
        self.assertEqual(coord.upgrades()[0]["status"], "completed")

    def test_status(self):
        coord = ClusterCoordinator()
        coord.add_node(Node(id="", address="a"))
        status = coord.status()
        self.assertIn("nodes", status)
        self.assertIn("zones", status)


if __name__ == "__main__":
    unittest.main()