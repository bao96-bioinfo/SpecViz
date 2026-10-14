"""Cleanup-only compatibility for owned display adapters from retired beta."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from bundle import BundleError

MARKER = "specviz-display"
RUNTIME_FILES = {"specviz_bridge.py", "specviz/display.py"}


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
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def identity(project: Path) -> str:
    return hashlib.sha256(str(project.resolve()).encode("utf-8")).hexdigest()


def _unhook(settings, host, entry):
    hook = entry.get("hook")
    if host == "claude-code":
        group = settings.get("hooks", {})
        entries = group.get("SessionStart", []) if isinstance(group, dict) else None
        if not isinstance(entries, list) or hook not in entries:
            raise BundleError(
                "Owned session hook was edited; preserve/reconcile the edit before migration"
            )
        entries.remove(hook)
        if not entries:
            group.pop("SessionStart", None)
        if not group:
            settings.pop("hooks", None)
    else:
        if settings.get(MARKER) != {"SessionStart": [hook]}:
            raise BundleError(
                "Owned SpecViz hook conflicts with an edit; preserve/reconcile it before migration"
            )
        settings.pop(MARKER)


def _cleanup(transaction, folder, registry, configurations, notices):
    runtime = folder / "runtime"
    # Preserve collectors still named by custom settings after unregistration.
    values = json.dumps(configurations)
    if str(runtime) in values or "specviz_bridge.py" in values:
        notices.append(
            f"Collector retained because a custom host setting still references it: {runtime}"
        )
        return False
    expected = registry.get("runtime_files", {})
    if not isinstance(expected, dict) or not set(expected) <= RUNTIME_FILES:
        raise BundleError("Invalid legacy dispatcher ownership record")
    for name, fingerprint in expected.items():
        path = runtime / name
        if not path.exists():
            continue
        if (
            path.is_symlink()
            or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != fingerprint
        ):
            notices.append(f"Edited collector retained: {path}")
            return False  # Keep its unchanged dependencies and cache as well.
    for name in expected:
        path = runtime / name
        if not path.exists():
            continue
        transaction.stage_file(path, None)
        # Interpreter-generated caches are disposable only for an unchanged,
        # owned source. Other runtime files remain untouched.
        cache = path.parent / "__pycache__"
        if cache.is_dir() and not cache.is_symlink():
            for compiled in cache.glob(path.stem + ".cpython-*.pyc"):
                if compiled.is_file() and not compiled.is_symlink():
                    transaction.stage_file(compiled, None)
    return True


def _cache_cleanup(transaction, folder, host, project_key, notices):
    directory = folder / "display" / host / project_key
    if not directory.exists():
        return
    if directory.is_symlink():
        notices.append(f"Linked display cache retained: {directory}")
        return
    context_keys = {
        "schema_version",
        "host",
        "surface",
        "project",
        "session",
        "generation",
        "started_at",
        "mode",
    }
    measurement_keys = {
        "schema_version",
        "host",
        "surface",
        "project",
        "session",
        "generation",
        "observed_at",
        "columns",
        "version",
        "mode",
        "origin",
    }
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        try:
            value = read(path)
            expected = (
                context_keys
                if path.name == "context.json"
                else measurement_keys
                if path.name == "measurement.json"
                else set()
            )
            valid = (
                set(value) == expected
                and value.get("schema_version") == 1
                and value.get("host") == host
                and value.get("project") == project_key
                and isinstance(value.get("session"), str)
                and path.parent.name
                == hashlib.sha256(value["session"].encode()).hexdigest()
            )
            if valid:
                transaction.stage_file(path, None)
            else:
                notices.append(f"Unrecognized display cache retained: {path}")
        except BundleError:
            notices.append(f"Edited display cache retained: {path}")


def configure(
    transaction, project: Path, home: Path, retained: set[str], affected: set[str]
):
    """Remove selected registrations transactionally; never create providers."""
    records, notices = {}, []
    for host in sorted(affected & {"claude-code", "antigravity"}):
        folder = home / ".specviz/adapters" / host
        if host == "claude-code":
            folder /= identity(project)
        registry_path = folder / "registry.json"
        registry = read(registry_path)
        if not registry:
            continue
        if (
            registry.get("schema_version") != 1
            or registry.get("host") != host
            or not isinstance(registry.get("projects"), dict)
        ):
            raise BundleError(
                f"Unrecognized display dispatcher ownership: {registry_path}"
            )
        key = identity(project)
        entry = registry["projects"].get(key)
        settings_path = (
            project / ".claude/settings.local.json"
            if host == "claude-code"
            else home / ".gemini/antigravity-cli/settings.json"
        )
        hooks_path = (
            settings_path if host == "claude-code" else project / ".agents/hooks.json"
        )
        if host in retained:
            if entry:
                records[host] = {
                    "registry": str(registry_path),
                    "settings": str(settings_path),
                    "hooks": str(hooks_path),
                }
            continue  # Another host in this same legacy skill still needs it.
        if not entry:
            continue
        if entry.get("project") != str(project):
            raise BundleError("Legacy registration does not match the selected project")
        settings = read(settings_path)
        hooks = settings if hooks_path == settings_path else read(hooks_path)
        _unhook(hooks, host, entry)
        del registry["projects"][key]
        remove_cache = True
        if not registry["projects"]:
            current = settings.get("statusLine")
            written = registry.get("owned_status", {})
            original = registry.get("original_status")
            if isinstance(current, dict):
                for field, value in written.items():
                    if current.get(field) == value:
                        if original is not None and field in original:
                            current[field] = copy.deepcopy(original[field])
                        else:
                            current.pop(field, None)
                if not current:
                    settings.pop("statusLine", None)
            other_settings = [
                read(project / ".claude/settings.json"),
                read(home / ".claude/settings.json"),
            ]
            remove_cache = _cleanup(
                transaction,
                folder,
                registry,
                [settings, hooks, *other_settings],
                notices,
            )
            registry.pop("owned_status", None)
        if remove_cache:
            _cache_cleanup(transaction, folder, host, key, notices)
        transaction.stage_file(settings_path, encoded(settings) if settings else None)
        if hooks_path != settings_path:
            transaction.stage_file(hooks_path, encoded(hooks) if hooks else None)
        # Keep the empty ownership record for diagnostics and retained edits.
        transaction.stage_file(registry_path, encoded(registry))
    return records, notices
