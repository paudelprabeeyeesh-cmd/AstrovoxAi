import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Subject:
    id: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    roles: List[str] = field(default_factory=list)
    clearances: List[str] = field(default_factory=list)


@dataclass
class Resource:
    id: str
    type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    owners: List[str] = field(default_factory=list)


class ABACEngine:
    def __init__(self) -> None:
        self._policy_attrs: List[Dict[str, Any]] = []

    def add_policy(self, effect: str, conditions: Dict[str, Any], actions: Optional[List[str]] = None) -> None:
        self._policy_attrs.append({"effect": effect, "conditions": conditions, "actions": actions or []})

    def evaluate(self, subject: Subject, resource: Resource, action: str) -> bool:
        attrs = {**subject.attributes, **resource.attributes, "action": action}
        for policy in self._policy_attrs:
            if policy["actions"] and action not in policy["actions"]:
                continue
            if all(attrs.get(k) == v for k, v in policy["conditions"].items()):
                return policy["effect"] == "allow"
        return False


class ReBACEngine:
    def __init__(self) -> None:
        self._relations: Dict[str, Dict[str, List[str]]] = {}

    def add_relation(self, subject_id: str, relation: str, object_id: str) -> None:
        self._relations.setdefault(subject_id, {}).setdefault(relation, []).append(object_id)

    def has_relation(self, subject_id: str, relation: str, object_id: str, max_depth: int = 3) -> bool:
        queue = [(subject_id, 0)]
        visited = {subject_id}
        while queue:
            current, depth = queue.pop(0)
            for obj in self._relations.get(current, {}).get(relation, []):
                if obj == object_id:
                    return True
                if depth + 1 < max_depth and obj not in visited:
                    visited.add(obj)
                    queue.append((obj, depth + 1))
        return False


class PBACEngine:
    def __init__(self) -> None:
        self._policies: List[Dict[str, Any]] = []

    def add_policy(self, effect: str, rules: List[Dict[str, Any]]) -> None:
        self._policies.append({"effect": effect, "rules": rules})

    def evaluate(self, subject: Subject, resource: Resource, action: str, context: Dict[str, Any]) -> bool:
        for policy in self._policies:
            if all(self._match(r, subject, resource, action, context) for r in policy["rules"]):
                return policy["effect"] == "allow"
        return False

    @staticmethod
    def _match(rule: Dict[str, Any], subject: Subject, resource: Resource, action: str, context: Dict[str, Any]) -> bool:
        if rule.get("action") and rule["action"] != action:
            return False
        if rule.get("resource_type") and rule["resource_type"] != resource.type:
            return False
        if rule.get("has_role"):
            return rule["has_role"] in subject.roles
        if rule.get("has_attribute"):
            return rule["has_attribute"] in subject.attributes
        return True


class AccessControl:
    def __init__(self) -> None:
        self._abac = ABACEngine()
        self._rebac = ReBACEngine()
        self._pbac = PBACEngine()
        self._roles: Dict[str, List[str]] = {}
        self._clearances: Dict[str, List[str]] = {}
        self._dacl: Dict[str, List[Dict[str, Any]]] = {}

    def add_role(self, role: str, perms: List[str]) -> None:
        self._roles[role] = perms

    def add_clearance(self, subject: str, levels: List[str]) -> None:
        self._clearances[subject] = levels

    def add_dacl(self, object_id: str, ace: List[Dict[str, Any]]) -> None:
        self._dacl[object_id] = ace

    def abac_allow(self, subject: Subject, resource: Resource, action: str) -> bool:
        return self._abac.evaluate(subject, resource, action)

    def rebac_allow(self, subject_id: str, relation: str, object_id: str) -> bool:
        return self._rebac.has_relation(subject_id, relation, object_id)

    def pbac_allow(self, subject: Subject, resource: Resource, action: str, context: Dict[str, Any]) -> bool:
        return self._pbac.evaluate(subject, resource, action, context)

    def dacl_allow(self, subject: Subject, object_id: str, access: str) -> bool:
        for ace in self._dacl.get(object_id, []):
            if ace.get("access") == access:
                if ace.get("role") in subject.roles:
                    return ace.get("effect") == "allow"
        return False
