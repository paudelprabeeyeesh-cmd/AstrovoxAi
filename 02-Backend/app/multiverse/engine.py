import hashlib
import json
import math
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import (
    BranchType,
    DivergencePoint,
    ParallelRun,
    ScenarioResult,
    Timeline,
    Universe,
    UniverseDiff,
    UniverseStatus,
)


class MultiverseEngine:
    def __init__(self):
        self.timelines: Dict[str, Timeline] = {}
        self.universes: Dict[str, Universe] = {}
        self.divergences: List[DivergencePoint] = []
        self.scenario_runs: List[ScenarioResult] = []
        self.parallel_runs: List[ParallelRun] = []
        self.diffs: List[UniverseDiff] = []
        self.message_histories: Dict[str, List[Dict[str, Any]]] = {}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _id(self) -> str:
        return uuid.uuid4().hex

    def create_timeline(self, user_id: str, name: str, description: Optional[str] = None, branch_type: BranchType = BranchType.CONVERSATION) -> Timeline:
        timeline_id = self._id()
        root_universe_id = self._id()
        root_universe = Universe(
            id=root_universe_id,
            user_id=user_id,
            name=f"Root: {name}",
            description=description,
            status=UniverseStatus.ACTIVE,
            branch_type=branch_type,
            generation=0,
            created_at=self._now(),
            updated_at=self._now(),
        )
        self.universes[root_universe_id] = root_universe
        self.message_histories[root_universe_id] = []

        timeline = Timeline(
            id=timeline_id,
            user_id=user_id,
            name=name,
            description=description,
            root_universe_id=root_universe_id,
            universes=[root_universe],
            created_at=self._now(),
            updated_at=self._now(),
        )
        self.timelines[timeline_id] = timeline
        return timeline

    def get_timeline(self, timeline_id: str, user_id: str) -> Optional[Timeline]:
        timeline = self.timelines.get(timeline_id)
        if timeline and timeline.user_id == user_id:
            return timeline
        return None

    def list_timelines(self, user_id: str) -> List[Timeline]:
        return [t for t in self.timelines.values() if t.user_id == user_id]

    def fork_universe(self, timeline_id: str, user_id: str, name: str, prompt_variant: Optional[str] = None, model_override: Optional[str] = None, temperature_override: Optional[float] = None, fork_point_message_id: Optional[int] = None) -> Optional[Universe]:
        timeline = self.get_timeline(timeline_id, user_id)
        if not timeline:
            return None

        root_id = timeline.root_universe_id
        parent = self.universes.get(root_id)
        if not parent:
            return None

        messages = self.message_histories.get(root_id, [])
        history = []
        if fork_point_message_id is not None:
            history = [m for m in messages if m.get("id") is not None and m["id"] <= fork_point_message_id]
        else:
            history = list(messages)

        fork_id = self._id()
        fork_universe = Universe(
            id=fork_id,
            user_id=user_id,
            name=name,
            description=f"Fork from {parent.name}",
            status=UniverseStatus.FORKED,
            branch_type=parent.branch_type,
            parent_universe_id=parent.id,
            root_universe_id=timeline.root_universe_id,
            generation=parent.generation + 1,
            parameters={
                **(parent.parameters or {}),
                "prompt_variant": prompt_variant or "",
                "model_override": model_override or "",
                "temperature_override": temperature_override if temperature_override is not None else 0.7,
            },
            created_at=self._now(),
            updated_at=self._now(),
        )
        self.universes[fork_id] = fork_universe
        self.message_histories[fork_id] = list(history)
        timeline.universes.append(fork_universe)
        timeline.updated_at = self._now()
        return fork_universe

    def send_message(self, universe_id: str, user_id: str, role: str, content: str, model_used: Optional[str] = None) -> Optional[Dict[str, Any]]:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return None

        messages = self.message_histories.setdefault(universe_id, [])
        message = {
            "id": len(messages) + 1,
            "role": role,
            "content": content,
            "model_used": model_used,
            "created_at": self._now().isoformat(),
        }
        messages.append(message)
        universe.message_count = len(messages)
        universe.updated_at = self._now()

        if universe.parent_universe_id:
            self._record_divergence_if_needed(universe.parent_universe_id, universe_id)

        return message

    def get_messages(self, universe_id: str, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return []
        messages = self.message_histories.get(universe_id, [])
        return messages[offset: offset + limit]

    def collapse_universe(self, universe_id: str, user_id: str) -> bool:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return False
        universe.status = UniverseStatus.COLLAPSED
        universe.updated_at = self._now()
        return True

    def merge_universes(self, source_universe_id: str, target_universe_id: str, user_id: str, strategy: str = "prefer_target", conflict_resolution: Optional[str] = None) -> Optional[UniverseDiff]:
        source = self.universes.get(source_universe_id)
        target = self.universes.get(target_universe_id)
        if not source or not target or source.user_id != user_id or target.user_id != user_id:
            return None

        source_messages = self.message_histories.get(source_universe_id, [])
        target_messages = self.message_histories.get(target_universe_id, [])
        diff = self._compute_diff(source_messages, target_messages)
        merged_messages = list(target_messages)

        if strategy == "interleave":
            merged = []
            max_len = max(len(source_messages), len(target_messages))
            for i in range(max_len):
                if i < len(target_messages):
                    merged.append(target_messages[i])
                if i < len(source_messages) and strategy == "interleave":
                    merged.append(source_messages[i])
            merged_messages = merged
        elif strategy == "prefer_source":
            merged_messages = list(source_messages)

        merged_id = self._id()
        merged_universe = Universe(
            id=merged_id,
            user_id=user_id,
            name=f"Merged: {source.name} + {target.name}",
            description=f"Merge of {source.name} into {target.name}",
            status=UniverseStatus.MERGED,
            branch_type=source.branch_type,
            parent_universe_id=target.id,
            root_universe_id=target.root_universe_id or source.root_universe_id,
            generation=max(source.generation, target.generation) + 1,
            parameters={**(target.parameters or {}), "merged_from": source.id, "merge_strategy": strategy},
            created_at=self._now(),
            updated_at=self._now(),
        )
        self.universes[merged_id] = merged_universe
        self.message_histories[merged_id] = merged_messages

        diff_obj = UniverseDiff(
            id=self._id(),
            source_universe_id=source_universe_id,
            target_universe_id=target_universe_id,
            diff=diff,
            summary=f"Merged {len(source_messages)} source messages with {len(target_messages)} target messages using strategy '{strategy}'",
            created_at=self._now(),
        )
        self.diffs.append(diff_obj)
        return diff_obj

    def _compute_diff(self, source_messages: List[Dict[str, Any]], target_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        diff = []
        max_len = max(len(source_messages), len(target_messages))
        for i in range(max_len):
            s = source_messages[i] if i < len(source_messages) else None
            t = target_messages[i] if i < len(target_messages) else None
            if s and t:
                if s.get("content") != t.get("content"):
                    diff.append({"index": i, "type": "modified", "source": s, "target": t})
            elif s and not t:
                diff.append({"index": i, "type": "added_in_source", "source": s})
            elif t and not s:
                diff.append({"index": i, "type": "added_in_target", "target": t})
        return diff

    def run_what_if_scenario(self, universe_id: str, user_id: str, scenario_id: str, variables: Dict[str, Any], iterations: int = 1, compare_against: Optional[str] = None) -> List[ScenarioResult]:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return []

        results = []
        base_messages = self.message_histories.get(universe_id, [])
        for i in range(iterations):
            simulated_history = list(base_messages)
            for key, value in variables.items():
                for msg in simulated_history:
                    if msg.get("role") == "user" and key.lower() in msg.get("content", "").lower():
                        msg["content"] = msg["content"].replace(key, value)

            final_content = simulated_history[-1]["content"] if simulated_history else ""
            result = ScenarioResult(
                id=self._id(),
                scenario_id=scenario_id,
                universe_id=universe_id,
                iteration=i + 1,
                result={"final_content": final_content, "variables_applied": variables, "message_count": len(simulated_history)},
                tokens_used=len(final_content.split()),
                latency_ms=random.randint(80, 500),
                created_at=self._now(),
            )
            results.append(result)
        self.scenario_runs.extend(results)
        return results

    def run_parallel_variants(self, universe_id: str, user_id: str, variants: List[Dict[str, Any]]) -> ParallelRun:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            raise ValueError("Universe not found or access denied")

        base_messages = self.message_histories.get(universe_id, [])
        run_results = []
        for variant in variants:
            simulated = []
            temperature = variant.get("temperature", 0.7)
            system_override = variant.get("system_prompt_override")
            for msg in base_messages:
                copy = dict(msg)
                if system_override and msg.get("role") == "system":
                    copy["content"] = system_override
                simulated.append(copy)

            final = simulated[-1]["content"] if simulated else ""
            run_results.append({
                "model": variant.get("model", "unknown"),
                "label": variant.get("label"),
                "temperature": temperature,
                "result": final,
                "tokens_used": len(final.split()),
                "latency_ms": random.randint(80, 500),
            })

        run = ParallelRun(
            id=self._id(),
            universe_id=universe_id,
            variants=variants,
            results=run_results,
            status="completed",
            created_at=self._now(),
        )
        self.parallel_runs.append(run)
        return run

    def get_visualization(self, timeline_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        timeline = self.get_timeline(timeline_id, user_id)
        if not timeline:
            return None

        nodes = []
        edges = []
        for universe in timeline.universes:
            nodes.append({
                "id": universe.id,
                "label": universe.name,
                "status": universe.status.value,
                "generation": universe.generation,
                "message_count": universe.message_count,
            })
            if universe.parent_universe_id:
                edges.append({"from": universe.parent_universe_id, "to": universe.id, "type": universe.branch_type.value})

        return {
            "timeline_id": timeline.id,
            "timeline_name": timeline.name,
            "nodes": nodes,
            "edges": edges,
            "total_universes": len(nodes),
        }

    def export_timeline(self, timeline_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        timeline = self.get_timeline(timeline_id, user_id)
        if not timeline:
            return None
        payload = {
            "timeline": {
                "id": timeline.id,
                "name": timeline.name,
                "description": timeline.description,
                "root_universe_id": timeline.root_universe_id,
                "created_at": timeline.created_at.isoformat(),
                "updated_at": timeline.updated_at.isoformat(),
            },
            "universes": [],
            "messages": {},
        }
        for universe in timeline.universes:
            payload["universes"].append({
                "id": universe.id,
                "name": universe.name,
                "status": universe.status.value,
                "branch_type": universe.branch_type.value,
                "parent_universe_id": universe.parent_universe_id,
                "generation": universe.generation,
                "created_at": universe.created_at.isoformat(),
                "updated_at": universe.updated_at.isoformat(),
            })
            payload["messages"][universe.id] = self.message_histories.get(universe.id, [])
        return payload

    def import_timeline(self, user_id: str, payload: Dict[str, Any]) -> Optional[Timeline]:
        timeline_data = payload.get("timeline")
        if not timeline_data:
            return None

        timeline_id = self._id()
        root_id = timeline_data.get("root_universe_id") or self._id()
        root_universe = Universe(
            id=root_id,
            user_id=user_id,
            name=timeline_data.get("name", "Imported Timeline"),
            description=timeline_data.get("description"),
            status=UniverseStatus.ACTIVE,
            created_at=datetime.fromisoformat(timeline_data.get("created_at", self._now().isoformat())),
            updated_at=datetime.fromisoformat(timeline_data.get("updated_at", self._now().isoformat())),
        )
        self.universes[root_id] = root_universe
        self.message_histories[root_id] = payload.get("messages", {}).get(root_id, [])

        for u in payload.get("universes", []):
            if u["id"] == root_id:
                continue
            universe = Universe(
                id=u["id"],
                user_id=user_id,
                name=u.get("name", "Imported Universe"),
                status=UniverseStatus(u.get("status", UniverseStatus.ACTIVE.value)),
                branch_type=BranchType(u.get("branch_type", BranchType.CONVERSATION.value)),
                parent_universe_id=u.get("parent_universe_id"),
                root_universe_id=root_id,
                generation=u.get("generation", 0),
                created_at=datetime.fromisoformat(u.get("created_at", self._now().isoformat())),
                updated_at=datetime.fromisoformat(u.get("updated_at", self._now().isoformat())),
            )
            self.universes[u["id"]] = universe
            self.message_histories[u["id"]] = payload.get("messages", {}).get(u["id"], [])

        timeline = Timeline(
            id=timeline_id,
            user_id=user_id,
            name=timeline_data.get("name", "Imported Timeline"),
            description=timeline_data.get("description"),
            root_universe_id=root_id,
            universes=list(self.universes.values()),
            created_at=self._now(),
            updated_at=self._now(),
        )
        self.timelines[timeline_id] = timeline
        return timeline

    def debug_meta_reality(self, universe_id: str, user_id: str) -> Dict[str, Any]:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return {"error": "Universe not found"}

        messages = self.message_histories.get(universe_id, [])
        role_counts: Dict[str, int] = {}
        for msg in messages:
            role_counts[msg.get("role", "unknown")] = role_counts.get(msg.get("role", "unknown"), 0) + 1

        return {
            "universe_id": universe.id,
            "name": universe.name,
            "status": universe.status.value,
            "generation": universe.generation,
            "message_count": len(messages),
            "role_distribution": role_counts,
            "parameters": universe.parameters,
            "created_at": universe.created_at.isoformat(),
            "updated_at": universe.updated_at.isoformat(),
            "parent_chain": self._get_parent_chain(universe_id),
            "active_branches": len([u for u in self.universes.values() if u.root_universe_id == universe.root_universe_id and u.status == UniverseStatus.ACTIVE]),
        }

    def _get_parent_chain(self, universe_id: str) -> List[Dict[str, Any]]:
        chain = []
        current = self.universes.get(universe_id)
        while current:
            chain.append({
                "id": current.id,
                "name": current.name,
                "generation": current.generation,
            })
            if not current.parent_universe_id:
                break
            current = self.universes.get(current.parent_universe_id)
        return chain

    def _record_divergence_if_needed(self, parent_id: str, child_id: str) -> None:
        parent_msgs = {m["id"]: m for m in self.message_histories.get(parent_id, [])}
        child_msgs = {m["id"]: m for m in self.message_histories.get(child_id, [])}
        common_ids = set(parent_msgs.keys()) & set(child_msgs.keys())
        for msg_id in common_ids:
            p = parent_msgs[msg_id]
            c = child_msgs[msg_id]
            if p.get("content") != c.get("content"):
                similarity = self._similarity(p.get("content", ""), c.get("content", ""))
                self.divergences.append(DivergencePoint(
                    id=self._id(),
                    universe_a=parent_id,
                    universe_b=child_id,
                    message_id=msg_id,
                    content_a=p.get("content", ""),
                    content_b=c.get("content", ""),
                    similarity=similarity,
                    divergence_type="content_drift",
                    created_at=self._now(),
                ))

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a and not set_b:
            return 1.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0

    def edit_reality(self, universe_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return None

        if "name" in updates and updates["name"] is not None:
            universe.name = updates["name"]
        if "description" in updates and updates["description"] is not None:
            universe.description = updates["description"]
        if "status" in updates and updates["status"] is not None:
            universe.status = updates["status"]
        if "parameters" in updates and isinstance(updates["parameters"], dict):
            universe.parameters = {**(universe.parameters or {}), **updates["parameters"]}

        universe.updated_at = self._now()
        return {
            "id": universe.id,
            "name": universe.name,
            "description": universe.description,
            "status": universe.status.value,
            "parameters": universe.parameters,
            "updated_at": universe.updated_at.isoformat(),
        }

    def manipulate_continuum(self, universe_id: str, user_id: str, manipulation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return None

        generation_shift = manipulation.get("generation_shift")
        if generation_shift is not None:
            universe.generation = max(0, universe.generation + generation_shift)

        temperature_override = manipulation.get("temperature_override")
        if temperature_override is not None:
            universe.parameters = {**(universe.parameters or {}), "temperature_override": temperature_override}

        time_delta = manipulation.get("time_delta_seconds")
        if time_delta is not None:
            from datetime import timedelta
            universe.updated_at = universe.updated_at + timedelta(seconds=time_delta)

        simulate_time_travel = manipulation.get("simulate_time_travel")
        if simulate_time_travel:
            universe.parameters = {**(universe.parameters or {}), "time_travel_simulated": True, "last_manipulation": self._now().isoformat()}

        collapse_probability = manipulation.get("collapse_probability")
        if collapse_probability is not None and random.random() < collapse_probability:
            universe.status = UniverseStatus.COLLAPSED
            universe.parameters = {**(universe.parameters or {}), "collapsed_by_continuum": True}

        universe.updated_at = self._now()
        return {
            "id": universe.id,
            "name": universe.name,
            "generation": universe.generation,
            "status": universe.status.value,
            "parameters": universe.parameters,
            "updated_at": universe.updated_at.isoformat(),
        }

    def construct_universe(self, user_id: str, timeline_id: str, blueprint: Dict[str, Any]) -> Optional[Universe]:
        timeline = self.timelines.get(timeline_id)
        if not timeline or timeline.user_id != user_id:
            return None

        universe_id = self._id()
        universe = Universe(
            id=universe_id,
            user_id=user_id,
            name=blueprint.get("name", f"Constructed Universe {self._id()[:8]}"),
            description=blueprint.get("description"),
            status=UniverseStatus.ACTIVE,
            branch_type=blueprint.get("branch_type", BranchType.CONVERSATION),
            root_universe_id=timeline.root_universe_id,
            generation=0,
            parameters={
                **(blueprint.get("parameters") or {}),
                "blueprint_name": blueprint.get("name", "default"),
                "temperature": blueprint.get("temperature", 0.7),
                "system_prompt_override": blueprint.get("system_prompt_override", ""),
            },
            created_at=self._now(),
            updated_at=self._now(),
        )
        self.universes[universe_id] = universe
        self.message_histories[universe_id] = []
        timeline.universes.append(universe)
        timeline.updated_at = self._now()
        return universe

    def run_safe_recursive_branch(self, universe_id: str, user_id: str, max_depth: int = 3, branching_factor: int = 2, prompt_variants: List[str] = None, model_override: Optional[str] = None) -> List[Universe]:
        universe = self.universes.get(universe_id)
        if not universe or universe.user_id != user_id:
            return []

        prompt_variants = prompt_variants or [f"Variant {i+1}" for i in range(branching_factor)]
        created: List[Universe] = []
        self._recursive_branch_inner(universe_id, user_id, max_depth, branching_factor, prompt_variants, model_override, 0, created)
        return created

    def _recursive_branch_inner(self, parent_id: str, user_id: str, max_depth: int, branching_factor: int, prompt_variants: List[str], model_override: Optional[str], current_depth: int, created: List[Universe]) -> None:
        if current_depth >= max_depth:
            return

        for i, variant in enumerate(prompt_variants[:branching_factor]):
            fork_id = self._id()
            parent = self.universes.get(parent_id)
            if not parent:
                continue

            messages = self.message_histories.get(parent_id, [])
            fork_universe = Universe(
                id=fork_id,
                user_id=user_id,
                name=f"{parent.name} → Recursion L{current_depth+1} V{i+1}",
                description=f"Recursive branch depth {current_depth + 1}",
                status=UniverseStatus.FORKED,
                branch_type=parent.branch_type,
                parent_universe_id=parent.id,
                root_universe_id=parent.root_universe_id,
                generation=parent.generation + 1,
                parameters={
                    **(parent.parameters or {}),
                    "recursive_depth": current_depth + 1,
                    "prompt_variant": variant,
                    "model_override": model_override or "",
                    "safe_termination_max_depth": max_depth,
                },
                created_at=self._now(),
                updated_at=self._now(),
            )
            self.universes[fork_id] = fork_universe
            self.message_histories[fork_id] = list(messages)
            created.append(fork_universe)

            if parent.root_universe_id:
                timeline = next((t for t in self.timelines.values() if t.root_universe_id == parent.root_universe_id), None)
                if timeline:
                    timeline.universes.append(fork_universe)
                    timeline.updated_at = self._now()

            self._recursive_branch_inner(fork_id, user_id, max_depth, branching_factor, prompt_variants, model_override, current_depth + 1, created)

    def portal_navigate(self, universe_id: str, user_id: str, target_universe_id: str, merge_on_arrival: bool = False) -> Optional[Dict[str, Any]]:
        source = self.universes.get(universe_id)
        target = self.universes.get(target_universe_id)
        if not source or not target or source.user_id != user_id or target.user_id != user_id:
            return None

        if merge_on_arrival:
            return self.merge_universes(universe_id, target_universe_id, user_id, strategy="interleave")

        return {
            "source_universe_id": universe_id,
            "source_name": source.name,
            "target_universe_id": target_universe_id,
            "target_name": target.name,
            "target_status": target.status.value,
            "target_generation": target.generation,
            "target_message_count": target.message_count,
            "navigation_type": "portal_jump",
            "arrival_timestamp": self._now().isoformat(),
        }
