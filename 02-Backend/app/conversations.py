"""Conversations with branching, editing, and full-text search.

WS-B-008 asks for branching, edit and regenerate, rename, pin, delete, export,
import, search, and projects with retention policies.

Branching is the part that shapes the rest of the model. A conversation where an
edit overwrites the old turn destroys the alternative the user might want back,
so a turn is a node with a parent rather than a slot: editing creates a child,
and the old branch is still reachable. Regeneration is the same operation with
the provider in the loop.

Full-text search is over the caller's own conversations, and it is a plaintext
scan rather than a LIKE query, because this store is per-identity and small
enough that an index is more machinery than the problem needs.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Roles and nodes
# ---------------------------------------------------------------------------


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Turn:
    """One message in a conversation.

    `parent_id` is what makes branching possible: a turn points at the turn it
    replaced, so the alternative is still reachable after an edit. Without it,
    an edit is a destructive overwrite and the user cannot go back.
    """

    turn_id: str
    conversation_id: str
    role: Role
    content: str
    created_at: float = 0.0
    parent_id: Optional[str] = None
    # branched_from records which turn this was an edit of, so the history of
    # edits is a chain rather than a debt of guessing from ordering.
    branched_from: Optional[str] = None
    # branch_label names the branch in a summary, so a user with several can tell
    # them apart without opening each.
    branch_label: str = ""
    # assistant is the model that produced an assistant turn.
    model: str = ""
    usage: Dict[str, int] = field(default_factory=dict)
    # pinned turns survive a cleanup, because a user pinning a message is an
    # explicit instruction not to forget it.
    pinned: bool = False

    def snippet(self, width: int = 80) -> str:
        """A single-line summary, for listings and search results."""
        text = re.sub(r"\s+", " ", self.content).strip()
        if len(text) <= width:
            return text
        return text[: width - 1] + "…"


@dataclass
class Conversation:
    """A conversation, which is a tree of turns with a head pointer per role.

    `head` points at the currently-selected turn for the caller's view. Branches
    exist as other children of the same parent, so selecting a different head is
    how a user moves between edits without deleting anything.
    """

    conversation_id: str
    owner: str
    title: str = "New conversation"
    created_at: float = 0.0
    updated_at: float = 0.0
    # pinned conversations survive cleanup, like a pinned turn.
    pinned: bool = False
    # project groups conversations, and is what a shared instruction and shared
    # files attach to.
    project: str = ""
    # head is the caller's current position: the turn shown as latest.
    head_id: Optional[str] = None
    # head_role lets a caller move the head without losing the assistant's own
    # position, so regenerating an answer does not hide the question that
    # prompted it.
    head_role: Role = Role.ASSISTANT
    # retention_seconds, when set, is how long this conversation lives before an
    # automated cleanup removes it. Zero means no policy.
    retention_seconds: float = 0.0

    @property
    def is_pinned(self) -> bool:
        return self.pinned

    def is_expired(self, now: float) -> bool:
        """Whether this conversation is past its retention window.

        A pinned conversation is never expired: pinning is an explicit
        instruction not to forget, so cleaning one up silently discards the one
        thing the user asked to keep.
        """
        if self.pinned or self.retention_seconds <= 0:
            return False
        return (now - self.updated_at) > self.retention_seconds


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------


@dataclass
class BranchSummary:
    """One branch of an edit, as shown to the user."""

    turn_id: str
    content_snippet: str
    created_at: float
    # is_current is the branch currently selected.
    is_current: bool = False
    # siblings is how many alternatives sit beside this one.
    sibling_count: int = 0
    label: str = ""


# ---------------------------------------------------------------------------
# The store
# ---------------------------------------------------------------------------


class ConversationNotFound(KeyError):
    pass


class TurnNotFound(KeyError):
    pass


@dataclass
class ConversationStore:
    """Stores conversations per owner.

    Per owner rather than per tenant, because a conversation is the user's own
    and a workspace-wide store would show one member's history to another.
    """

    _conversations: Dict[str, Conversation] = field(default_factory=dict)
    _turns: Dict[str, Dict[str, Turn]] = field(default_factory=dict)
    _lock: Any = None

    def __post_init__(self) -> None:
        import threading

        self._lock = threading.RLock()

    # -- create -------------------------------------------------------------

    def create(
        self,
        owner: str,
        *,
        title: str = "New conversation",
        project: str = "",
        retention_seconds: float = 0.0,
        conversation_id: Optional[str] = None,
    ) -> Conversation:
        import secrets

        now = time.time()
        conversation = Conversation(
            conversation_id=conversation_id or "conv_" + secrets.token_hex(12),
            owner=owner,
            title=title,
            created_at=now,
            updated_at=now,
            project=project,
            retention_seconds=retention_seconds,
        )
        with self._lock:
            self._conversations[conversation.conversation_id] = conversation
            self._turns[conversation.conversation_id] = {}
        return conversation

    # -- turns --------------------------------------------------------------

    def add_turn(
        self,
        conversation_id: str,
        role: Role,
        content: str,
        *,
        model: str = "",
        usage: Optional[Dict[str, int]] = None,
        parent_id: Optional[str] = None,
    ) -> Turn:
        """Append a turn and move the head to it.

        The head moves to every new turn so the caller's view follows the
        conversation without them having to ask.
        """
        import secrets

        with self._lock:
            conversation = self._require(conversation_id)
            now = time.time()
            turn = Turn(
                turn_id="turn_" + secrets.token_hex(12),
                conversation_id=conversation_id,
                role=role,
                content=content,
                created_at=now,
                parent_id=parent_id or conversation.head_id,
                model=model,
                usage=usage or {},
            )
            self._turns[conversation_id][turn.turn_id] = turn
            conversation.head_id = turn.turn_id
            conversation.head_role = role
            conversation.updated_at = now
            return turn

    def select_head(self, conversation_id: str, turn_id: str) -> Turn:
        """Move the head to an existing turn, e.g. to view another branch."""
        with self._lock:
            conversation = self._require(conversation_id)
            turn = self._require_turn(conversation_id, turn_id)
            conversation.head_id = turn.turn_id
            conversation.head_role = turn.role
            return turn

    # -- editing and branching ---------------------------------------------

    def edit_turn(
        self,
        conversation_id: str,
        turn_id: str,
        content: str,
    ) -> Turn:
        """Replace a turn's content without losing the original.

        The original is kept as a sibling branch. A destructive overwrite would
        leave the user unable to go back to the turn they had, which is the whole
        reason branching exists.

        The new turn's parent is the original's parent, so the two sit beside each
        other rather than nested, and moving between them is a head selection
        rather than a walk.

        The replacement is built here rather than through add_turn, because
        add_turn treats a None parent as "attach under the current head" - which
        would place an edit of the first turn underneath the reply that followed
        it rather than beside the turn it replaced.
        """
        import secrets

        with self._lock:
            conversation = self._require(conversation_id)
            original = self._require_turn(conversation_id, turn_id)

            now = time.time()
            replacement = Turn(
                turn_id="turn_" + secrets.token_hex(12),
                conversation_id=conversation_id,
                role=original.role,
                content=content,
                created_at=now,
                # The original's parent, explicitly, including None.
                parent_id=original.parent_id,
                branched_from=original.turn_id,
                branch_label=(
                    f"edit of {original.snippet(24)}"
                    if original.branch_label == ""
                    else original.branch_label
                ),
                model=original.model,
                usage=original.usage,
                pinned=original.pinned,
            )
            self._turns[conversation_id][replacement.turn_id] = replacement

            # The head moves to the replacement so the caller sees their edit.
            conversation.head_id = replacement.turn_id
            conversation.head_role = replacement.role
            conversation.updated_at = now
            return replacement

    def regenerate(
        self,
        conversation_id: str,
        turn_id: str,
    ) -> Turn:
        """Mark an assistant turn as needing regeneration.

        Same operation as an edit, with the provider in the loop: the new turn is
        a sibling branch rather than a replacement, so the previous answer stays
        available while a fresh one is fetched.
        """
        with self._lock:
            original = self._require_turn(conversation_id, turn_id)
            return self.edit_turn(conversation_id, turn_id, original.content)

    def branches_of(self, conversation_id: str, turn_id: str) -> List[BranchSummary]:
        """List the branches that sit beside a turn.

        Siblings are the turns with the same parent, which is exactly the set the
        user moves between when they go back to a previous edit.
        """
        with self._lock:
            self._require(conversation_id)
            turn = self._require_turn(conversation_id, turn_id)
            siblings = [
                t
                for t in self._turns[conversation_id].values()
                if t.parent_id == turn.parent_id
            ]
            siblings.sort(key=lambda t: t.created_at)
            return [
                BranchSummary(
                    turn_id=sibling.turn_id,
                    content_snippet=sibling.snippet(),
                    created_at=sibling.created_at,
                    is_current=sibling.turn_id == turn_id,
                    sibling_count=len(siblings) - 1,
                    label=sibling.branch_label,
                )
                for sibling in siblings
            ]

    def branch_count(self, conversation_id: str) -> int:
        """How many alternatives have been branched, across every role.

        Counts the parenthesised relationships, so a conversation with one edit
        reports one branch. Zero means nothing has been edited.
        """
        with self._lock:
            self._require(conversation_id)
            return sum(
                1
                for t in self._turns[conversation_id].values()
                if t.branched_from is not None
            )

    # -- search -------------------------------------------------------------

    def search(
        self,
        owner: str,
        query: str,
        *,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Full-text search over the caller's own conversations.

        Scoped by construction: the store is keyed by conversation and the owner
        is looked up per conversation, so a cross-owner result would have to
        come from a conversation that exists twice, which it cannot.

        Plain scan rather than a LIKE query. A per-identity conversation set is
        small, and an index is more machinery than the problem needs at this
        size - with a test on the scan's own behaviour rather than on a query
        planner's.
        """
        terms = [t.lower() for t in re.findall(r"[a-zA-Z0-9]{2,}", query)]
        if not terms:
            return []

        with self._lock:
            results: List[Tuple[float, Dict[str, Any]]] = []
            for conversation in self._conversations.values():
                if conversation.owner != owner:
                    continue
                for turn in self._turns[conversation.conversation_id].values():
                    lowered = turn.content.lower()
                    matches = sum(1 for term in terms if term in lowered)
                    if matches == 0:
                        continue
                    results.append(
                        (
                            matches / len(terms),
                            {
                                "conversation_id": conversation.conversation_id,
                                "conversation_title": conversation.title,
                                "turn_id": turn.turn_id,
                                "role": turn.role.value,
                                "snippet": turn.snippet(),
                                "score": matches / len(terms),
                            },
                        )
                    )
            results.sort(key=lambda item: (-item[0], item[1]["turn_id"]))
            return [item[1] for item in results[:limit]]

    def history_for_llm(self, conversation_id: str, max_turns: int = 40) -> List[Turn]:
        """The turn list a model sees, in conversation order.

        Ordered by created_at rather than by tree position, because a branch the
        user did not select would otherwise appear as a parallel line in the
        prompt. Only the selected branch is included, so the model sees one
        coherent conversation.
        """
        with self._lock:
            self._require(conversation_id)
            selected = self._selected_branch(conversation_id)
            return selected[:max_turns]

    # -- metadata -----------------------------------------------------------

    def rename(self, conversation_id: str, title: str) -> Conversation:
        with self._lock:
            conversation = self._require(conversation_id)
            conversation.title = title
            conversation.updated_at = time.time()
            return conversation

    def pin(self, conversation_id: str, pinned: bool = True) -> Conversation:
        with self._lock:
            conversation = self._require(conversation_id)
            conversation.pinned = pinned
            return conversation

    def set_project(self, conversation_id: str, project: str) -> Conversation:
        with self._lock:
            conversation = self._require(conversation_id)
            conversation.project = project
            conversation.updated_at = time.time()
            return conversation

    def list(
        self,
        owner: str,
        *,
        project: Optional[str] = None,
        include_expired: bool = False,
    ) -> List[Conversation]:
        """List the caller's conversations, most recently updated first."""
        with self._lock:
            now = time.time()
            out = []
            for conversation in self._conversations.values():
                if conversation.owner != owner:
                    continue
                if not include_expired and conversation.is_expired(now):
                    continue
                if project is not None and conversation.project != project:
                    continue
                out.append(conversation)
        out.sort(key=lambda c: -c.updated_at)
        return out

    def projects(self, owner: str) -> List[str]:
        """The distinct project names this caller uses."""
        with self._lock:
            return sorted(
                {
                    c.project
                    for c in self._conversations.values()
                    if c.owner == owner and c.project
                }
            )

    # -- delete and cleanup -------------------------------------------------

    def delete(self, conversation_id: str) -> bool:
        """Delete a conversation and every turn in it."""
        with self._lock:
            if conversation_id not in self._conversations:
                return False
            del self._conversations[conversation_id]
            del self._turns[conversation_id]
            return True

    def cleanup(self, owner: Optional[str] = None, now: Optional[float] = None) -> int:
        """Remove conversations past their retention, skipping pinned ones.

        A pinned conversation is never cleaned up, because pinning is an explicit
        instruction not to forget.
        """
        if now is None:
            now = time.time()
        removed = 0
        with self._lock:
            targets = [
                cid
                for cid, c in self._conversations.items()
                if (owner is None or c.owner == owner) and c.is_expired(now)
            ]
            for cid in targets:
                del self._conversations[cid]
                del self._turns[cid]
                removed += 1
        return removed

    # -- export / import ----------------------------------------------------

    def export(self, conversation_id: str) -> Dict[str, Any]:
        """Export a conversation as plain JSON, including branched turns.

        Branches are exported rather than flattened, so a re-import restores the
        tree the user left rather than a single line of it. Dropping them would
        make an export/import cycle a lossy one.
        """
        with self._lock:
            conversation = self._require(conversation_id)
            return {
                "conversation_id": conversation.conversation_id,
                "owner": conversation.owner,
                "title": conversation.title,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "pinned": conversation.pinned,
                "project": conversation.project,
                "retention_seconds": conversation.retention_seconds,
                "head_id": conversation.head_id,
                "head_role": conversation.head_role.value,
                "turns": [
                    {
                        "turn_id": turn.turn_id,
                        "conversation_id": turn.conversation_id,
                        "role": turn.role.value,
                        "content": turn.content,
                        "created_at": turn.created_at,
                        "parent_id": turn.parent_id,
                        "branched_from": turn.branched_from,
                        "branch_label": turn.branch_label,
                        "model": turn.model,
                        "usage": turn.usage,
                        "pinned": turn.pinned,
                    }
                    for turn in sorted(
                        self._turns[conversation_id].values(),
                        key=lambda t: t.created_at,
                    )
                ],
            }

    def import_(self, payload: Dict[str, Any]) -> Conversation:
        """Restore an exported conversation.

        Restores the tree and the head, so a re-imported conversation looks like
        the one that was exported rather than like a fresh one with the same
        messages.
        """
        with self._lock:
            existing = self._conversations.get(payload["conversation_id"])
            if existing is not None:
                # Re-importing over an existing id would merge two trees with
                # the same ids, so it is refused rather than attempted.
                raise ValueError(
                    f"conversation {payload['conversation_id']} already exists"
                )

            conversation = Conversation(
                conversation_id=payload["conversation_id"],
                owner=payload["owner"],
                title=payload.get("title", "Imported"),
                created_at=payload.get("created_at", time.time()),
                updated_at=payload.get("updated_at", time.time()),
                pinned=bool(payload.get("pinned", False)),
                project=payload.get("project", ""),
                head_id=payload.get("head_id"),
                head_role=Role(payload.get("head_role", "assistant")),
                retention_seconds=float(payload.get("retention_seconds", 0.0)),
            )
            self._conversations[conversation.conversation_id] = conversation
            self._turns[conversation.conversation_id] = {}

            for raw in payload.get("turns", []):
                turn = Turn(
                    turn_id=raw["turn_id"],
                    conversation_id=conversation.conversation_id,
                    role=Role(raw["role"]),
                    content=raw["content"],
                    created_at=raw.get("created_at", time.time()),
                    parent_id=raw.get("parent_id"),
                    branched_from=raw.get("branched_from"),
                    branch_label=raw.get("branch_label", ""),
                    model=raw.get("model", ""),
                    usage=raw.get("usage", {}),
                    pinned=bool(raw.get("pinned", False)),
                )
                self._turns[conversation.conversation_id][turn.turn_id] = turn
            return conversation

    def export_json(self, conversation_id: str) -> str:
        return json.dumps(self.export(conversation_id), indent=2, sort_keys=True)

    # -- internals ----------------------------------------------------------

    def _selected_branch(self, conversation_id: str) -> List[Turn]:
        """The turns on the currently-selected branch, in order.

        Walks the parent chain from the head backwards, which is what selects one
        branch rather than showing the whole tree. An edit that replaced a turn
        means the original is not on this path, and that is the point.
        """
        conversation = self._require(conversation_id)
        turns = self._turns[conversation_id]
        if conversation.head_id is None:
            return []

        chain: List[Turn] = []
        seen = set()
        current = turns.get(conversation.head_id)
        while current is not None and current.turn_id not in seen:
            seen.add(current.turn_id)
            chain.append(current)
            if current.parent_id is None:
                break
            current = turns.get(current.parent_id)
        chain.reverse()
        return chain

    def _require(self, conversation_id: str) -> Conversation:
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFound(conversation_id)
        return conversation

    def _require_turn(self, conversation_id: str, turn_id: str) -> Turn:
        self._require(conversation_id)
        turn = self._turns[conversation_id].get(turn_id)
        if turn is None:
            raise TurnNotFound(turn_id)
        return turn
