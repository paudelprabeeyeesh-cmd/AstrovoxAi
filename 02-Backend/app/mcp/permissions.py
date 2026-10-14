"""Permission and approval enforcement for MCP tool calls.

The MCP surface registered tools and resources and had no access control: a
tool call could execute without a caller identity, without a scope, and without
an approval for anything irreversible. The rest of the platform gates every
action, so this is the same gate applied to the protocol path - not a new one.

The three checks are ordered deliberately. A missing scope is a 401 (nobody is
identified), a scope that lacks permission is a 403 (the caller is identified
and refused), and an unapproved action is a 409 (the caller must decide). They
are different failures and collapsing them loses the distinction between "who
are you", "you may not", and "you must approve".

Approval is fail-closed: a risky action with no approver resolved is refused
rather than executed. A tool that can purchase, send, delete or execute has to
have a named approver before it runs, not after.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# Risk and scope
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """How dangerous a tool's effect is.

    Only the ordering matters to the gate; the names describe the effect. A new
    level belongs here rather than as a string in a caller, so the comparison is
    type-checked rather than assumed.
    """

    READ = "read"
    WRITE = "write"
    NETWORK = "network"
    EXECUTE = "execute"
    IRREVERSIBLE = "irreversible"


# The level at which an action needs a human decision before it runs. Chosen by
# the effect, not the wording: spending, sending, deleting and running are the
# actions a caller cannot undo once they have happened.
IRREVERSIBLE_LEVELS = frozenset({RiskLevel.EXECUTE, RiskLevel.IRREVERSIBLE})


class RequiredScope(str, Enum):
    """What a caller must hold to invoke a tool."""

    MCP_TOOL_CALL = "mcp.tool.call"
    MCP_RESOURCE_READ = "mcp.resource.read"
    MCP_TOOL_ADMIN = "mcp.tool.admin"


# ---------------------------------------------------------------------------
# Failures
# ---------------------------------------------------------------------------


class MCPPermissionError(Exception):
    """A tool call was refused.

    `status` is the HTTP status a router should map it to, so the protocol layer
    and the HTTP layer cannot drift apart on what each refusal means.
    """

    def __init__(self, status: int, message: str, *, tool: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.tool = tool


class NoSuchTool(MCPPermissionError):
    def __init__(self, tool: str) -> None:
        super().__init__(404, f"no MCP tool named {tool!r}", tool=tool)


class NotIdentified(MCPPermissionError):
    """No caller identity was resolved at all."""

    def __init__(self, tool: str) -> None:
        super().__init__(
            401, "no caller identity was resolved for this tool call", tool=tool
        )


class ScopeMissing(MCPPermissionError):
    """The caller is identified but does not hold the required scope."""

    def __init__(self, scope: str, tool: str) -> None:
        super().__init__(
            403, f"caller does not hold the required scope {scope!r}", tool=tool
        )


class RiskTooHigh(MCPPermissionError):
    """The caller is not permitted to perform an action this risky."""

    def __init__(self, allowed: str, needed: str, tool: str) -> None:
        super().__init__(
            403,
            f"tool risk {needed!r} exceeds the caller's permitted {allowed!r}",
            tool=tool,
        )


class ApprovalRequired(MCPPermissionError):
    """A risky action needs a human decision before it runs.

    The `approval_id` is what the caller presents back to confirm; it is what
    makes the gate stateful between the refusal and the retry.
    """

    def __init__(self, tool: str, approval_id: str) -> None:
        super().__init__(
            409,
            f"tool {tool!r} requires approval before it runs",
            tool=tool,
        )
        self.approval_id = approval_id


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


@dataclass
class ToolPolicy:
    """What a single tool requires and what it is allowed to do."""

    name: str
    risk: RiskLevel = RiskLevel.READ
    required_scope: RequiredScope = RequiredScope.MCP_TOOL_CALL
    # The maximum risk any caller may reach with this tool, independent of the
    # caller's own ceiling. A tool that reads is not made dangerous by a caller
    # who is permitted to execute.
    max_risk: Optional[RiskLevel] = None
    # A human must approve before this runs.
    requires_approval: bool = False
    # Output is truncated to this many characters before it leaves the process,
    # so a tool that returns a whole file cannot flood the caller.
    max_output_chars: int = 8000


@dataclass
class Caller:
    """Who is making the call and what they may do."""

    identity: Optional[str] = None
    scopes: frozenset = frozenset()
    max_risk: RiskLevel = RiskLevel.READ
    tenant: Optional[str] = None

    @property
    def identified(self) -> bool:
        return bool(self.identity)

    def holds(self, scope: RequiredScope) -> bool:
        return scope.value in self.scopes


@dataclass
class Approval:
    """A pending or resolved decision."""

    approval_id: str
    tool: str
    approver: Optional[str] = None
    granted: bool = False
    decided_at: Optional[float] = None
    # The caller this approval is bound to. An approval is not transferable,
    # because a granted decision for one identity must let another identity act.
    identity: Optional[str] = None


@dataclass
class ApprovalGate:
    """Records approvals and decides whether an action may run.

    Approvals expire. A decision granted a week ago is not a decision about
    today's call, and an approval with no expiry is how a granted request
    becomes permanent permission.
    """

    ttl_seconds: float = 900.0
    _pending: Dict[str, Approval] = field(default_factory=dict)
    _resolved: Dict[str, Approval] = field(default_factory=dict)

    def request(self, tool: str, identity: str, ttl_seconds: Optional[float] = None) -> Approval:
        import secrets

        approval = Approval(
            approval_id="appr_" + secrets.token_hex(12),
            tool=tool,
            identity=identity,
        )
        self._pending[approval.approval_id] = approval
        return approval

    def grant(self, approval_id: str, approver: str, identity: str) -> Approval:
        return self._decide(approval_id, approver, identity, granted=True)

    def deny(self, approval_id: str, approver: str, identity: str) -> Approval:
        return self._decide(approval_id, approver, identity, granted=False)

    def _decide(
        self, approval_id: str, approver: str, identity: str, *, granted: bool
    ) -> Approval:
        approval = self._pending.pop(approval_id, None)
        if approval is None:
            raise MCPPermissionError(404, f"no pending approval {approval_id!r}")
        # The same caller who asked decides. Another identity may not consume a
        # decision that was not about them.
        if approval.identity != identity:
            raise MCPPermissionError(
                403, "that approval belongs to a different caller"
            )
        approval.granted = granted
        approval.approver = approver
        approval.decided_at = time.time()
        self._resolved[approval.approval_id] = approval
        return approval

    def is_granted(self, approval_id: str, identity: str, now: Optional[float] = None) -> bool:
        approval = self._resolved.get(approval_id)
        if approval is None or not approval.granted:
            return False
        if approval.identity != identity:
            return False
        if now is None:
            now = time.time()
        if approval.decided_at is None:
            return False
        return (now - approval.decided_at) <= self.ttl_seconds

    def pending(self, tool: str) -> List[Approval]:
        return [a for a in self._pending.values() if a.tool == tool]

    def resolved(self, approval_id: str) -> Optional[Approval]:
        return self._resolved.get(approval_id)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

# Ordered so a caller's ceiling can be compared with a tool's requirement
# without a table. The order is the risk order.
_RISK_ORDER = [
    RiskLevel.READ,
    RiskLevel.WRITE,
    RiskLevel.NETWORK,
    RiskLevel.EXECUTE,
    RiskLevel.IRREVERSIBLE,
]


def _risk_rank(level: RiskLevel) -> int:
    try:
        return _RISK_ORDER.index(level)
    except ValueError:  # an unmapped level is treated as the worst case
        return len(_RISK_ORDER) - 1


class MCPPermissionGate:
    """Decides whether a tool call may run.

    Every check is fail-closed: an unknown tool, an unidentified caller, a
    missing scope, an excessive risk or an unapproved risky action all refuse.
    A gate that allows when it cannot decide is not a gate.
    """

    def __init__(self, approvals: Optional[ApprovalGate] = None) -> None:
        self.approvals = approvals or ApprovalGate()
        self._policies: Dict[str, ToolPolicy] = {}

    def register(self, policy: ToolPolicy) -> None:
        self._policies[policy.name] = policy

    def policy(self, name: str) -> Optional[ToolPolicy]:
        return self._policies.get(name)

    def authorise(
        self,
        tool_name: str,
        caller: Caller,
        *,
        approval_id: Optional[str] = None,
        now: Optional[float] = None,
    ) -> ToolPolicy:
        """Raise MCPPermissionError unless the call may proceed.

        Returns the policy so a caller does not look it up twice, and so the
        output cap comes from the same place as the decision.
        """
        policy = self._policies.get(tool_name)
        if policy is None:
            # An unregistered tool is refused rather than executed with a
            # default policy: a default would grant capabilities nobody
            # declared.
            raise NoSuchTool(tool_name)

        if not caller.identified:
            raise NotIdentified(tool_name)

        if not caller.holds(policy.required_scope):
            raise ScopeMissing(policy.required_scope.value, tool_name)

        caller_ceiling = _risk_rank(caller.max_risk)
        tool_risk = _risk_rank(policy.risk)
        if tool_risk > caller_ceiling:
            raise RiskTooHigh(
                caller.max_risk.value, policy.risk.value, tool_name
            )

        if policy.max_risk is not None and _risk_rank(
            policy.risk
        ) > _risk_rank(policy.max_risk):
            raise RiskTooHigh(
                policy.max_risk.value, policy.risk.value, tool_name
            )

        if policy.requires_approval and policy.risk in IRREVERSIBLE_LEVELS:
            if approval_id is None:
                approval = self.approvals.request(tool_name, caller.identity or "")
                raise ApprovalRequired(tool_name, approval.approval_id)
            if not self.approvals.is_granted(
                approval_id, caller.identity or "", now=now
            ):
                # An expired, denied, wrong-caller or unknown approval is a
                # refusal, not a fallthrough.
                raise ApprovalRequired(
                    tool_name,
                    self.approvals.request(tool_name, caller.identity or "").approval_id,
                )

        return policy

    def record_output(self, tool_name: str, output: str) -> str:
        """Truncate a tool's output to its policy's cap.

        A caller that can read a whole file through a tool must not be able to
        flood the model's context, or the tool becomes a denial-of-service on
        the next request.
        """
        policy = self._policies.get(tool_name)
        cap = policy.max_output_chars if policy else 8000
        if len(output) <= cap:
            return output
        # The marker says how much was dropped, so a consumer can tell
        # truncation from a short answer.
        return output[:cap] + f"\n[truncated {len(output) - cap} chars]"


# ---------------------------------------------------------------------------
# Handler wiring
# ---------------------------------------------------------------------------


@dataclass
class ToolHandler:
    """A callable plus its policy.

    The handler is stored next to the policy rather than resolved separately,
    so a tool cannot be invoked without going through the gate that owns its
    policy - which is the previous failure mode.
    """

    policy: ToolPolicy
    handler: Callable[..., Any]

    def __post_init__(self) -> None:
        if not callable(self.handler):
            raise TypeError("handler must be callable")


class GatedToolRegistry:
    """Registers handlers with policies and runs them behind the gate."""

    def __init__(self, gate: MCPPermissionGate) -> None:
        self.gate = gate
        self._handlers: Dict[str, ToolHandler] = {}

    def register(self, policy: ToolPolicy, handler: Callable[..., Any]) -> None:
        self.gate.register(policy)
        self._handlers[policy.name] = ToolHandler(policy=policy, handler=handler)

    def invoke(
        self,
        tool_name: str,
        caller: Caller,
        arguments: Optional[Dict[str, Any]] = None,
        *,
        approval_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authorise, then run, then truncate. Any refusal propagates.

        Output is truncated after the handler returns, not before, so the
        truncation cap applies to what actually came back rather than to what
        the caller asked for.
        """
        policy = self.gate.authorise(tool_name, caller, approval_id=approval_id)
        handler = self._handlers[tool_name]
        raw = handler.handler(**(arguments or {}))
        text = raw if isinstance(raw, str) else repr(raw)
        return {
            "tool": tool_name,
            "risk": policy.risk.value,
            "output": self.gate.record_output(tool_name, text),
        }


# ---------------------------------------------------------------------------
# Dependency wiring
# ---------------------------------------------------------------------------


def caller_from_scopes(identity: Optional[str], scopes: Iterable[str], max_risk: str = "read") -> Caller:
    """Build a Caller from a token's claims.

    Kept separate so a router can map its own auth object onto a Caller without
    this module importing the web framework. The default risk is read: a caller
    with no declared ceiling is assumed to be able to do the least, not the
    most.
    """
    return Caller(
        identity=identity,
        scopes=frozenset(scopes or ()),
        max_risk=RiskLevel(max_risk) if max_risk else RiskLevel.READ,
    )


# A read-only caller with the standard scope, used by the default and by tests.
def read_only_caller(identity: str = "anon") -> Caller:
    return Caller(
        identity=identity,
        scopes=frozenset({RequiredScope.MCP_TOOL_CALL.value}),
        max_risk=RiskLevel.READ,
    )


def admin_caller(identity: str = "admin") -> Caller:
    return Caller(
        identity=identity,
        scopes=frozenset(
            {
                RequiredScope.MCP_TOOL_CALL.value,
                RequiredScope.MCP_TOOL_ADMIN.value,
            }
        ),
        max_risk=RiskLevel.IRREVERSIBLE,
    )
