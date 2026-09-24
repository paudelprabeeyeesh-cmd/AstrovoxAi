from advanced_security.access_control import (
    ABACEngine,
    AccessControl,
    PBACEngine,
    ReBACEngine,
    Subject,
)


class DummyResource:
    def __init__(self, id: str, type: str, attributes=None, owners=None):
        self.id = id
        self.type = type
        self.attributes = attributes or {}
        self.owners = owners or []


def test_abac_allow() -> None:
    engine = ABACEngine()
    engine.add_policy("allow", {"role": "admin", "action": "write"})
    subject = Subject(id="u1", attributes={"role": "admin"}, roles=["admin"])
    resource = DummyResource(id="r1", type="file")
    assert engine.evaluate(subject, resource, "write") is True


def test_abac_deny() -> None:
    engine = ABACEngine()
    engine.add_policy("allow", {"role": "admin", "action": "write"})
    subject = Subject(id="u1", attributes={"role": "user"}, roles=["user"])
    resource = DummyResource(id="r1", type="file")
    assert engine.evaluate(subject, resource, "write") is False


def test_rebac_allow() -> None:
    engine = ReBACEngine()
    engine.add_relation("u1", "parent", "u2")
    assert engine.has_relation("u1", "parent", "u2") is True
    assert engine.has_relation("u2", "parent", "u1") is False


def test_pbac_allow() -> None:
    engine = PBACEngine()
    subject = Subject(id="u1", attributes={"role": "viewer"}, roles=["viewer"])
    resource = DummyResource(id="r1", type="file")
    engine.add_policy("allow", [{"has_role": "viewer"}, {"resource_type": "file"}])
    assert engine.evaluate(subject, resource, "read", {}) is True


def test_access_control_dacl() -> None:
    ac = AccessControl()
    subject = Subject(id="u1", attributes={"role": "viewer"}, roles=["viewer"])
    ac.add_dacl("doc1", [{"access": "read", "role": "viewer", "effect": "allow"}])
    assert ac.dacl_allow(subject, "doc1", "read") is True


def test_access_control_abac() -> None:
    ac = AccessControl()
    subject = Subject(id="u1", attributes={"role": "admin"}, roles=["admin"])
    resource = DummyResource(id="r1", type="file", attributes={"owner": "alice"})
    ac._abac.add_policy("allow", {"role": "admin", "owner": "alice"})
    assert ac.abac_allow(subject, resource, "write") is True


def test_access_control_pbac() -> None:
    ac = AccessControl()
    subject = Subject(id="u1", attributes={"role": "viewer"}, roles=["viewer"])
    resource = DummyResource(id="r1", type="file")
    ac._pbac.add_policy("allow", [{"has_role": "viewer"}, {"resource_type": "file"}])
    assert ac.pbac_allow(subject, resource, "read", {}) is True


def test_rebac_indirect() -> None:
    engine = ReBACEngine()
    engine.add_relation("u1", "parent", "u2")
    engine.add_relation("u2", "parent", "u3")
    assert engine.has_relation("u1", "parent", "u3") is True
