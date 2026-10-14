"""Synthetic schema-1 beta installs, independent of the retired checkout.

Reproduces 0.2.0-beta.1 ownership, shared host registrations, callback settings,
and disposable display metadata. Callback source is inert and never executed.
"""

import copy
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

from bundle import fingerprint, identity as bundle_identity, source_files
from adapters import encoded, identity, MARKER, read


def seal_legacy(source):
    files = fingerprint(source_files(source))
    version = "0.2.0-beta.1"
    value = {
        "schema_version": 1,
        "channel": "beta",
        "version": version,
        "source_identity": bundle_identity("beta", version, files),
        "files": files,
    }
    (source / "release.json").write_bytes(encoded(value))
    return value


def seed(project, home, hosts, source):
    from test_install import installer

    project = project.resolve()
    home = home.resolve()
    release = json.loads((source / "release.json").read_text())
    for target in {project / installer.HOSTS[h] for h in hosts}:
        old = read(target / installer.MANIFEST)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)
        registrations = sorted(
            set(old.get("hosts", []))
            | {h for h in hosts if project / installer.HOSTS[h] == target}
        )
        manifest = {
            "owner": "specviz",
            "schema_version": 1,
            "version": release["version"],
            "channel": "beta",
            "source_identity": release["source_identity"],
            "scope": "project",
            "hosts": registrations,
            "generation_handoff": True,
            "files": {
                name: hashlib.sha256(p.read_bytes()).hexdigest()
                for name, p in source_files(source).items()
            },
            "display_adapters": {},
        }
        (target / installer.MANIFEST).write_bytes(encoded(manifest))
    for host in set(hosts) & {"claude-code", "antigravity"}:
        folder = home / ".specviz/adapters" / host
        if host == "claude-code":
            folder /= identity(project)
        registry_path = folder / "registry.json"
        registry = read(registry_path)
        settings_path = (
            project / ".claude/settings.local.json"
            if host == "claude-code"
            else home / ".gemini/antigravity-cli/settings.json"
        )
        hooks_path = (
            settings_path if host == "claude-code" else project / ".agents/hooks.json"
        )
        settings = read(settings_path)
        hooks = settings if hooks_path == settings_path else read(hooks_path)

        def command(action):
            parts = [
                sys.executable,
                str(folder / "runtime/specviz_bridge.py"),
                action,
                "--host",
                host,
                "--registry",
                str(registry_path),
            ]
            return (
                subprocess.list2cmdline(parts) if os.name == "nt" else shlex.join(parts)
            )

        raw_hook = {"type": "command", "command": command("session"), "timeout": 10}
        hook = (
            {"matcher": "", "hooks": [raw_hook]} if host == "claude-code" else raw_hook
        )
        if not registry:
            original = copy.deepcopy(settings.get("statusLine"))
            inherited = (
                read(project / ".claude/settings.json").get("statusLine")
                or read(home / ".claude/settings.json").get("statusLine")
                if host == "claude-code"
                else None
            )
            previous = original or inherited
            owned = copy.deepcopy(previous) if previous else {"type": "command"}
            owned["command"] = command("status")
            if host == "claude-code":
                owned["refreshInterval"] = 1
            elif not previous:
                owned["stack_with_default"] = True
            registry = {
                "schema_version": 1,
                "host": host,
                "projects": {},
                "original_status": original,
                "previous_status": previous,
                "owned_status": owned,
                "runtime_files": {},
            }
        settings["statusLine"] = copy.deepcopy(registry["owned_status"])
        if host == "claude-code":
            entries = hooks.setdefault("hooks", {}).setdefault("SessionStart", [])
            if hook not in entries:
                entries.append(hook)
        else:
            hooks[MARKER] = {"SessionStart": [hook]}
        registry["projects"][identity(project)] = {
            "project": str(project),
            "mode": "default",
            "hook": hook,
        }
        if host == "antigravity":
            registry["projects"][identity(project)]["settings_file"] = str(
                settings_path
            )
        for name, relative in [
            ("specviz_bridge.py", "scripts/specviz_bridge.py"),
            ("specviz/display.py", "scripts/specviz/display.py"),
        ]:
            target = folder / "runtime" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source / relative).read_bytes())
            registry["runtime_files"][name] = hashlib.sha256(
                target.read_bytes()
            ).hexdigest()
        for path, value in [
            (settings_path, settings),
            (hooks_path, hooks),
            (registry_path, registry),
        ]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(encoded(value))
        manifest_path = project / installer.HOSTS[host] / installer.MANIFEST
        manifest = read(manifest_path)
        manifest["display_adapters"][host] = {
            "registry": str(registry_path),
            "settings": str(settings_path),
            "hooks": str(hooks_path),
        }
        manifest_path.write_bytes(encoded(manifest))
        session = "legacy-session"
        directory = (
            folder
            / "display"
            / host
            / identity(project)
            / hashlib.sha256(session.encode()).hexdigest()
        )
        directory.mkdir(parents=True, exist_ok=True)
        common = {
            "schema_version": 1,
            "host": host,
            "surface": "chat",
            "project": identity(project),
            "session": session,
            "generation": "legacy-generation",
            "mode": "default",
        }
        (directory / "context.json").write_bytes(encoded(dict(common, started_at=1)))
        (directory / "measurement.json").write_bytes(
            encoded(
                dict(
                    common,
                    observed_at=2,
                    columns=120,
                    version="legacy",
                    origin="status-line",
                )
            )
        )
