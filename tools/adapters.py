"""Bounded, ownership-aware beta host setup. Stable can also remove beta setup."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from bundle import BundleError

MARKER = "specviz-display"


def read(path: Path) -> dict:
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise BundleError(f"Configuration contains a symbolic link: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError) as exc:
        raise BundleError(f"Cannot read host configuration: {path}") from exc
    if not isinstance(value, dict):
        raise BundleError(f"Host configuration must be an object: {path}")
    return value


def encoded(value: dict) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def identity(project: Path) -> str:
    return hashlib.sha256(str(project.resolve()).encode("utf-8")).hexdigest()


def command(arguments: list[str]) -> str:
    return subprocess.list2cmdline(arguments) if os.name == "nt" else shlex.join(arguments)


def configure(transaction, project: Path, home: Path, source: Path | None,
              desired: set[str], affected: set[str]) -> dict[str, dict]:
    """Stage all changes; never execute a user's status command at setup time."""
    records = {}
    base = home / ".specviz/adapters"
    for host in sorted(affected & {"claude-code", "antigravity"}):
        folder = base / host
        if host == "claude-code":
            folder /= identity(project)
        registry_path = folder / "registry.json"
        old = read(registry_path)
        if old and (old.get("schema_version") != 1 or old.get("host") != host):
            raise BundleError(f"Unrecognized display dispatcher ownership: {registry_path}")
        active = host in desired
        if not active and not old:
            continue
        settings_path = (project / ".claude/settings.local.json" if host == "claude-code"
                         else home / ".gemini/antigravity-cli/settings.json")
        hooks_path = settings_path if host == "claude-code" else project / ".agents/hooks.json"
        settings = read(settings_path)
        hooks = settings if hooks_path == settings_path else read(hooks_path)
        registry = copy.deepcopy(old) if old else {"schema_version": 1, "host": host, "projects": {}}
        entry_key = identity(project)
        old_entry = registry["projects"].get(entry_key)
        runtime = folder / "runtime"
        callback = [sys.executable, str(runtime / "specviz_bridge.py")]
        status_command = command(callback + ["status", "--host", host, "--registry", str(registry_path)])
        session_command = command(callback + ["session", "--host", host, "--registry", str(registry_path)])
        hook = ({"matcher": "", "hooks": [{"type": "command", "command": session_command, "timeout": 10}]}
                if host == "claude-code" else {"type": "command", "command": session_command, "timeout": 10})
        if active:
            if old.get("owned_status") and settings.get("statusLine") != old["owned_status"]:
                raise BundleError("SpecViz status-line settings were edited; preserve/reconcile those edits before updating beta")
            if not old.get("projects"):
                original = settings.get("statusLine")
                if original is not None and (not isinstance(original, dict) or original.get("type", "command") != "command"):
                    raise BundleError("Cannot compose this host status-line type")
                inherited = None
                if host == "claude-code" and original is None:
                    inherited = read(project / ".claude/settings.json").get("statusLine")
                    if inherited is None:
                        inherited = read(home / ".claude/settings.json").get("statusLine")
                previous = original if original is not None else inherited
                if previous and (not isinstance(previous, dict) or "specviz_bridge.py" in str(previous.get("command", ""))):
                    raise BundleError("Refusing to wrap an unowned or recursive SpecViz status line")
                registry["previous_status"] = copy.deepcopy(previous)
                registry["original_status"] = copy.deepcopy(original)
                configured = copy.deepcopy(previous) if previous else {"type": "command"}
                configured["command"] = status_command
                if host == "claude-code":
                    configured["refreshInterval"] = 1
                elif not previous:
                    configured["stack_with_default"] = True
                registry["owned_status"] = configured
            settings["statusLine"] = copy.deepcopy(registry["owned_status"])
            if old_entry and old_entry.get("hook") != hook:
                raise BundleError("Dispatcher interpreter changed; remove the existing beta registration before reinstalling")
            _hook(hooks, host, hook, old_entry, active=True)
            registry["projects"][entry_key] = {"project": str(project), "mode": "default", "hook": hook}
            if source is not None:
                runtime_files = {"specviz_bridge.py": source / "scripts/specviz_bridge.py",
                                 "specviz/display.py": source / "scripts/specviz/display.py"}
                for name, path in runtime_files.items():
                    if not path.is_file():
                        raise BundleError(f"Beta bundle is missing its display adapter: {name}")
                expected = old.get("runtime_files", {})
                if any(name not in runtime_files for name in expected):
                    raise BundleError("Invalid dispatcher ownership record")
                for name, fingerprint in expected.items():
                    path = runtime / name
                    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != fingerprint:
                        raise BundleError("Owned display dispatcher was edited; preserve it before updating")
                registry["runtime_files"] = {}
                for name, path in runtime_files.items():
                    target = runtime / name
                    if target.exists() and name not in expected:
                        raise BundleError(f"Unowned file conflicts with display dispatcher: {target}")
                    data = path.read_bytes()
                    transaction.stage_file(target, data)
                    registry["runtime_files"][name] = hashlib.sha256(data).hexdigest()
        elif old_entry:
            _hook(hooks, host, hook, old_entry, active=False)
            del registry["projects"][entry_key]
            if not registry["projects"]:
                current = settings.get("statusLine")
                written = registry.get("owned_status", {})
                original = registry.get("original_status")
                if isinstance(current, dict):
                    for key, value in written.items():
                        if current.get(key) == value:
                            if original is not None and key in original:
                                current[key] = original[key]
                            else:
                                current.pop(key, None)
                    if not current:
                        settings.pop("statusLine", None)
                # Keep the inert dispatcher to preserve later custom commands
                # that may reference it. There are no collecting registrations.
                registry.pop("owned_status", None)
        transaction.stage_file(settings_path, encoded(settings) if settings else None)
        if hooks_path != settings_path:
            transaction.stage_file(hooks_path, encoded(hooks) if hooks else None)
        transaction.stage_file(registry_path, encoded(registry))
        if active:
            records[host] = {"registry": str(registry_path), "settings": str(settings_path), "hooks": str(hooks_path)}
    return records


def _hook(settings: dict, host: str, hook: dict, entry: dict | None, *, active: bool):
    if host == "claude-code":
        group = settings.setdefault("hooks", {})
        if not isinstance(group, dict) or not isinstance(group.get("SessionStart", []), list):
            raise BundleError("Invalid SessionStart hook configuration")
        entries = group.setdefault("SessionStart", [])
        if entry and entry["hook"] not in entries:
            raise BundleError("Owned session hook was edited; preserve/reconcile the edit before changing channels")
        if entry:
            entries.remove(entry["hook"])
        if active:
            entries.append(hook)
        if not entries:
            group.pop("SessionStart", None)
        if not group:
            settings.pop("hooks", None)
    else:
        if MARKER in settings and (not entry or settings[MARKER] != {"SessionStart": [entry["hook"]]}):
            raise BundleError("A custom hook conflicts with the owned SpecViz hook")
        if active:
            settings[MARKER] = {"SessionStart": [hook]}
        elif entry:
            settings.pop(MARKER, None)
