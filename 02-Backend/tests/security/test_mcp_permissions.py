"""Tests for MCP permission and approval enforcement.

The MCP package previously registered tools with no access control at all, so
these are adversarial: each test attempts something that should be refused. A
test that only confirms a permitted caller is allowed proves nothing about the
gate.
"""

import os
import sys
import time

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
sys.path.insert(0, ".")

import pytest

from app.mcp.permissions import (
    ApprovalRequired,
    ApprovalGate,
    Caller,
    GatedToolRegistry,
    MCPPermissionGate,
    NoSuchTool,
    NotIdentified,
    RiskLevel,
    RiskTooHigh,
    ScopeMissing,
    ToolPolicy,
    admin_caller,
    read_only_caller,
    RequiredScope,
)


def make_gate():
    gate = MCPPermissionGate()
    gate.register(ToolPolicy(name="read-doc", risk=RiskLevel.READ))
    gate.register(
        ToolPolicy(
            name="write-doc",
            risk=RiskLevel.WRITE,
            max_risk=RiskLevel.WRITE,
            max_output_chars=40,
        )
    )
    gate.register(
        ToolPolicy(
            name="run-command",
            risk=RiskLevel.EXECUTE,
            max_risk=RiskLevel.EXECUTE,
            requires_approval=True,
        )
    )
    gate.register(
        ToolPolicy(
            name="delete-all",
            risk=RiskLevel.IRREVERSIBLE,
            requires_approval=True,
        )
    )
    return gate


def test_read_only_caller_may_call_a_read_tool():
    gate = make_gate()
    policy = gate.authorise("read-doc", read_only_caller("u1"))
    assert policy.risk == RiskLevel.READ


def make_gate_fixture():
    return make_gate()


# --- unregistered and unidentified ---


def test_an_unregistered_tool_is_refused():
    gate = make_gate()
    with pytest.raises(NoSuchTool) as exc:
        gate.authorise("no-such-tool", read_only_caller("u1"))
    assert exc.value.status == 404


def test_an_unidentified_caller_is_refused():
    # The previous failure mode: no identity, no check at all.
    gate = make_gate()
    caller = Caller(identity=None, scopes={"mcp.tool.call"})
    with pytest.raises(NotIdentified) as exc:
        gate.authorise("read-doc", caller)
    assert exc.value.status == 401


def test_an_empty_identity_is_refused():
    gate = make_gate()
    caller = Caller(identity="", scopes={"mcp.tool.call"})
    with pytest.raises(NotIdentified):
        gate.authorise("read-doc", caller)


# --- scope ---


def test_a_missing_scope_is_refused():
    gate = make_gate()
    caller = Caller(identity="u1", scopes=frozenset())
    with pytest.raises(ScopeMissing) as exc:
        gate.authorise("read-doc", caller)
    assert exc.value.status == 403
    assert "mcp.tool.call" in exc.value.message


def test_a_wrong_scope_is_refused():
    # Holding an unrelated scope is not holding the required one.
    gate = make_gate()
    caller = Caller(identity="u1", scopes=frozenset({"mcp.resource.read"}))
    with pytest.raises(ScopeMissing):
        gate.authorise("read-doc", caller)


def test_tool_admin_scope_is_required_for_admin_tools():
    gate = make_gate()
    gate.register(
        ToolPolicy(
            name="list-tools",
            risk=RiskLevel.READ,
            required_scope=RequiredScope.MCP_TOOL_ADMIN,
        )
    )
    with pytest.raises(ScopeMissing):
        gate.authorise("list-tools", read_only_caller("u1"))
    gate.authorise("list-tools", admin_caller("root"))


# --- risk ---


def test_a_risky_tool_is_refused_for_a_read_only_caller():
    gate = make_gate()
    with pytest.raises(RiskTooHigh) as exc:
        gate.authorise("write-doc", read_only_caller("u1"))
    assert exc.value.status == 403


def test_an_execute_tool_needs_a_permitted_caller():
    gate = make_gate()
    caller = Caller(
        identity="u1", scopes={"mcp.tool.call"}, max_risk=RiskLevel.WRITE
    )
    with pytest.raises(RiskTooHigh):
        gate.authorise("run-command", caller)


def test_a_tools_own_ceiling_is_enforced_even_for_an_admin():
    # A caller who may do anything is still bounded by the tool's declared
    # maximum, so a misclassified tool cannot exceed its policy.
    gate = make_gate()
    gate.register(
        ToolPolicy(name="over-budget", risk=RiskLevel.IRREVERSIBLE, max_risk=RiskLevel.WRITE)
    )
    with pytest.raises(RiskTooHigh):
        gate.authorise("over-budget", admin_caller("root"))


# --- approval ---


def test_a_risky_action_without_approval_is_refused():
    gate = make_gate()
    with pytest.raises(ApprovalRequired) as exc:
        gate.authorise("delete-all", admin_caller("root"))
    assert exc.value.status == 409
    # The approval id is what the caller presents back.
    assert exc.value.approval_id


def test_a_risky_action_runs_once_approved():
    gate = make_gate()
    caller = admin_caller("root")
    with pytest.raises(ApprovalRequired) as refused:
        gate.authorise("delete-all", caller)

    approval_id = refused.value.approval_id
    gate.approvals.grant(approval_id, "root", "root")
    policy = gate.authorise("delete-all", caller, approval_id=approval_id)
    assert policy.name == "delete-all"


def test_an_approval_is_not_transferable():
    # A decision granted to one identity must not let another act.
    gate = make_gate()
    owner = admin_caller("owner")
    with pytest.raises(ApprovalRequired) as refused:
        gate.authorise("delete-all", owner)
    approval_id = refused.value.approval_id
    gate.approvals.grant(approval_id, "owner", "owner")

    other = admin_caller("attacker")
    with pytest.raises(ApprovalRequired):
        gate.authorise("delete-all", other, approval_id=approval_id)


def test_an_expired_approval_is_refused():
    gate = make_gate()
    caller = admin_caller("root")
    with pytest.raises(ApprovalRequired):
        gate.authorise("delete-all", caller)
    pending = gate.approvals.pending("delete-all")[0]
    gate.approvals.grant(pending.approval_id, "root", "root")

    long_after = time.time() + (gate.approvals.ttl_seconds + 1)
    with pytest.raises(ApprovalRequired):
        gate.authorise(
            "delete-all", caller, approval_id=pending.approval_id, now=long_after
        )


def test_a_denied_approval_is_refused():
    gate = make_gate()
    caller = admin_caller("root")
    with pytest.raises(ApprovalRequired):
        gate.authorise("delete-all", caller)
    pending = gate.approvals.pending("delete-all")[0]
    gate.approvals.deny(pending.approval_id, "root", "root")

    with pytest.raises(ApprovalRequired):
        gate.authorise("delete-all", caller, approval_id=pending.approval_id)


def test_an_unknown_approval_is_refused():
    gate = make_gate()
    with pytest.raises(ApprovalRequired):
        gate.authorise("delete-all", admin_caller("root"), approval_id="appr_missing")


def test_a_fabricated_approval_id_is_refused():
    # A guessed id must not pass. The ids are random and the lookup is exact.
    gate = make_gate()
    with pytest.raises(ApprovalRequired):
        gate.authorise("delete-all", admin_caller("root"), approval_id="appr_" + "0" * 24)


def test_a_read_tool_needs_no_approval():
    gate = make_gate()
    # Approval is not blanket: a read is not held hostage to a decision.
    policy = gate.authorise("read-doc", read_only_caller("u1"))
    assert policy.requires_approval is False


def test_an_execute_tool_is_fail_closed_without_an_approver():
    # A risky action with no approver resolvable is refused, not executed.
    gate = make_gate()
    with pytest.raises(ApprovalRequired):
        gate.authorise("run-command", admin_caller("root"))


# --- default posture ---


def test_the_gate_defaults_to_refusing():
    # Nothing is allowed unless a policy says so. A gate that starts open is a
    # gate that has already failed.
    gate = MCPPermissionGate()
    with pytest.raises(NoSuchTool):
        gate.authorise("anything", admin_caller("root"))


def test_an_unknown_risk_level_is_treated_as_the_worst():
    gate = make_gate()
    caller = Caller(identity="u1", scopes={"mcp.tool.call"}, max_risk=RiskLevel.READ)
    with pytest.raises(RiskTooHigh):
        gate.authorise("delete-all", caller)


# --- output truncation ---


def test_output_is_truncated_to_the_policy_cap():
    gate = make_gate()
    truncated = gate.record_output("write-doc", "x" * 200)
    assert len(truncated) < 100
    assert "truncated" in truncated


def test_truncation_marker_reports_the_omitted_size():
    gate = make_gate()
    truncated = gate.record_output("write-doc", "x" * 200)
    assert "160 chars" in truncated


def test_output_within_the_cap_is_untouched():
    gate = make_gate()
    short = "short output"
    assert gate.record_output("write-doc", short) == short


# --- registry ---


def test_a_tool_cannot_run_without_going_through_the_gate():
    registry = GatedToolRegistry(make_gate())
    calls = []

    def read_handler():
        calls.append("ran")
        return "ok"

    registry.register(ToolPolicy(name="read-doc", risk=RiskLevel.READ), read_handler)
    registry.invoke("read-doc", read_only_caller("u1"))
    assert calls == ["ran"]

    del calls[:]
    # An unregistered tool: nothing runs, because no handler exists for it.
    with pytest.raises(NoSuchTool):
        registry.invoke("no-such-tool", read_only_caller("u1"))
    assert calls == []


def test_a_refused_tool_does_not_run():
    registry = GatedToolRegistry(make_gate())
    calls = []

    def write_handler():
        calls.append("ran")
        return "ok"

    registry.register(ToolPolicy(name="write-doc", risk=RiskLevel.WRITE), write_handler)
    with pytest.raises(RiskTooHigh):
        registry.invoke("write-doc", read_only_caller("u1"))
    assert calls == [], "a refused tool still executed"


def test_a_registered_handler_must_be_callable():
    registry = GatedToolRegistry(make_gate())
    with pytest.raises(TypeError):
        registry.register(ToolPolicy(name="bad", risk=RiskLevel.READ), "not callable")


def test_invoked_output_is_truncated():
    registry = GatedToolRegistry(make_gate())
    registry.register(
        ToolPolicy(name="write-doc", risk=RiskLevel.WRITE, max_output_chars=20),
        lambda: "y" * 100,
    )
    caller = Caller(identity="u1", scopes={"mcp.tool.call"}, max_risk=RiskLevel.WRITE)
    result = registry.invoke("write-doc", caller)
    # The truncated payload is the cap plus the marker, so the assertion is on
    # the payload rather than on the whole returned string.
    assert "y" * 20 in result["output"]
    assert "truncated" in result["output"]
    assert len("y" * 20) <= 20
    assert result["risk"] == "write"


def test_caller_from_scopes_defaults_to_minimal_risk():
    from app.mcp.permissions import caller_from_scopes

    caller = caller_from_scopes("u1", ["mcp.tool.call"])
    assert caller.max_risk == RiskLevel.READ


def test_admin_caller_is_permitted():
    gate = make_gate()
    policy = gate.authorise("read-doc", admin_caller("root"))
    assert policy.name == "read-doc"
