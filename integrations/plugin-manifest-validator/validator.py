import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]


REQUIRED_MANIFEST_FIELDS = {
    "name": str,
    "version": str,
    "description": str,
    "author": str,
    "main": str,
    "permissions": list,
}

OPTIONAL_MANIFEST_FIELDS = {
    "icon": str,
    "homepage": str,
    "repository": str,
    "license": str,
    "engines": dict,
    "dependencies": dict,
    "config_schema": dict,
    "hooks": list,
    "commands": list,
}

SEMVER_REGEX = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:-([\w.]+))?(?:\+([\w.]+))?$')
NAME_REGEX = re.compile(r'^[a-z0-9][a-z0-9\-\.]{1,63}$')


class PluginManifestValidator:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, manifest: Dict[str, Any]) -> ValidationResult:
        self.errors = []
        self.warnings = []
        self._check_required_fields(manifest)
        self._check_name(manifest.get("name", ""))
        self._check_version(manifest.get("version", ""))
        self._check_permissions(manifest.get("permissions", []))
        self._check_dependencies(manifest.get("dependencies", {}))
        self._check_hooks(manifest.get("hooks", []))
        self._check_config_schema(manifest.get("config_schema", {}))
        self._check_engines(manifest.get("engines", {}))
        return ValidationResult(valid=len(self.errors) == 0, errors=self.errors, warnings=self.warnings)

    def validate_file(self, path: str) -> ValidationResult:
        with open(path, 'r', encoding='utf-8') as f:
            try:
                manifest = json.load(f)
            except json.JSONDecodeError as e:
                return ValidationResult(valid=False, errors=[f"Invalid JSON: {e}"], warnings=[])
        return self.validate(manifest)

    def _check_required_fields(self, manifest: Dict[str, Any]):
        for field, expected_type in REQUIRED_MANIFEST_FIELDS.items():
            if field not in manifest:
                self.errors.append(f"Missing required field: {field}")
            elif not isinstance(manifest[field], expected_type):
                self.errors.append(f"Field '{field}' must be of type {expected_type.__name__}")

    def _check_name(self, name: Any):
        if not isinstance(name, str):
            return
        if not NAME_REGEX.match(name):
            self.errors.append(f"Plugin name '{name}' is invalid. Must be lowercase alphanumeric with dashes/dots.")
        if len(name) > 64:
            self.errors.append(f"Plugin name '{name}' exceeds 64 characters.")

    def _check_version(self, version: Any):
        if not isinstance(version, str):
            return
        if not SEMVER_REGEX.match(version):
            self.errors.append(f"Version '{version}' is not valid semver.")
        if version.startswith("0.0.0"):
            self.warnings.append(f"Version '{version}' appears to be a placeholder.")

    def _check_permissions(self, permissions: Any):
        if not isinstance(permissions, list):
            return
        valid_permissions = {"read", "write", "admin", "webhooks", "auth", "network", "filesystem"}
        for perm in permissions:
            if perm not in valid_permissions:
                self.warnings.append(f"Unknown permission: '{perm}'")

    def _check_dependencies(self, dependencies: Any):
        if not isinstance(dependencies, dict):
            return
        for dep, version in dependencies.items():
            if not isinstance(version, str):
                self.errors.append(f"Dependency '{dep}' version must be a string.")
                continue
            if not SEMVER_REGEX.match(version) and version not in {"*", "latest"}:
                self.warnings.append(f"Dependency '{dep}' version '{version}' may not be semver.")

    def _check_hooks(self, hooks: Any):
        if not isinstance(hooks, list):
            return
        valid_hooks = {"onInstall", "onUninstall", "onEnable", "onDisable", "onMessage", "onConversationCreate"}
        for hook in hooks:
            if hook not in valid_hooks:
                self.warnings.append(f"Unknown hook: '{hook}'")

    def _check_config_schema(self, schema: Any):
        if not isinstance(schema, dict):
            return
        if "type" not in schema:
            self.warnings.append("Config schema missing 'type' field.")

    def _check_engines(self, engines: Any):
        if not isinstance(engines, dict):
            return
        for engine, version in engines.items():
            if engine not in {"python", "node", "go", "rust"}:
                self.warnings.append(f"Unknown engine: '{engine}'")
            if not isinstance(version, str):
                self.errors.append(f"Engine '{engine}' version must be a string.")
