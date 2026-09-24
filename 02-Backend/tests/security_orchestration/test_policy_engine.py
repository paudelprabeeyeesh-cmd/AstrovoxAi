from security_orchestration.policy_engine import PolicyEngine, PolicyRule, Policy, RBACEngine


def test_evaluate_allow() -> None:
    engine = PolicyEngine()
    policy = Policy(id="p1", name="admin-write", effect="allow", priority=1, rules=[
        PolicyRule(name="allow-admin-write", conditions={"subject.role": "admin", "resource.type": "file"}, actions=["write"]),
    ])
    engine.add_policy(policy)
    result = engine.evaluate({"role": "admin"}, {"type": "file"}, "write")
    assert result == "allow"


def test_evaluate_deny() -> None:
    engine = PolicyEngine()
    policy = Policy(id="p1", name="admin-write", effect="allow", priority=1, rules=[
        PolicyRule(name="allow-admin-write", conditions={"subject.role": "admin", "resource.type": "file"}, actions=["write"]),
    ])
    engine.add_policy(policy)
    result = engine.evaluate({"role": "user"}, {"type": "file"}, "write")
    assert result == "deny"


def test_evaluate_default_no_policies() -> None:
    engine = PolicyEngine()
    assert engine.evaluate({}, {}, "read") == "deny"


def test_allowed_actions() -> None:
    engine = PolicyEngine()
    engine.add_policy(Policy(id="p1", name="perms", effect="allow", rules=[
        PolicyRule(name="file-actions", actions=["create", "read", "update"]),
    ]))
    result = engine.allowed_actions({"role": "user"}, {"type": "file"})
    assert "create" in result
    assert "read" in result
    assert "update" in result


def test_escalate() -> None:
    engine = PolicyEngine()
    engine.add_policy(Policy(id="p1", name="p", effect="deny", priority=1, rules=[
        PolicyRule(name="r1", conditions={"subject.role": "admin"}, actions=["write"]),
    ]))
    result = engine.escalate({"role": "admin"}, {"type": "file"}, "write")
    assert result is not None
    assert result[0]["policy"] == "p"
    assert "r1" in result[0]["rules"]


def test_escalate_no_match() -> None:
    engine = PolicyEngine()
    assert engine.escalate({}, {}, "read") is None


def test_priority_order() -> None:
    engine = PolicyEngine()
    engine.add_policy(Policy(id="p-low", name="low", effect="allow", priority=0, rules=[
        PolicyRule(name="r", actions=["read"]),
    ]))
    engine.add_policy(Policy(id="p-high", name="high", effect="deny", priority=10, rules=[
        PolicyRule(name="r", actions=["read"]),
    ]))
    assert engine.evaluate({}, {}, "read") == "deny"


def test_rbac_has_permission() -> None:
    rbac = RBACEngine()
    rbac.add_role("editor", ["read", "write"])
    assert rbac.has_permission("editor", "write") is True
    assert rbac.has_permission("editor", "delete") is False


def test_rbac_roles_for() -> None:
    rbac = RBACEngine()
    rbac.add_role("viewer", ["read"])
    rbac.add_role("editor", ["read", "write"])
    result = rbac.roles_for(["read", "write"])
    assert "editor" in result
    assert "viewer" not in result


def test_rbac_assign_permission() -> None:
    rbac = RBACEngine()
    rbac.add_role("viewer", ["read"])
    rbac.assign_permission("viewer", "list")
    assert rbac.has_permission("viewer", "list") is True


def test_match_rule_with_context() -> None:
    engine = PolicyEngine()
    engine.add_policy(Policy(id="p1", name="ctx", effect="allow", rules=[
        PolicyRule(name="r1", conditions={"clearance": "secret"}, actions=["read"]),
    ]))
    result = engine.evaluate({"role": "agent"}, {"type": "doc"}, "read", {"clearance": "secret"})
    assert result == "allow"
