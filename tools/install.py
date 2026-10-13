"""Install the maintained SpecViz skill into explicit project-owned locations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bundle import BundleError, CHANNELS, source_files, validate

SOURCE = Path(__file__).resolve().parents[1] / "skills/specviz"
MANIFEST = ".specviz-install.json"
HOSTS = {"codex": ".agents/skills/specviz", "claude-code": ".claude/skills/specviz", "antigravity": ".agents/skills/specviz"}


class InstallError(BundleError):
    pass


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_files(source: Path) -> dict[str, Path]:
    return source_files(source)


def _owned(target: Path) -> dict | None:
    manifest = target / MANIFEST
    if not target.exists():
        return None
    if not manifest.is_file() or manifest.is_symlink():
        raise InstallError(f"Existing skill is not managed by SpecViz: {target}")
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstallError(f"Invalid installation manifest: {target}") from exc
    if value.get("owner") != "specviz" or value.get("schema_version") != 1 or not isinstance(value.get("files"), dict):
        raise InstallError(f"Unrecognized installation ownership: {target}")
    value.setdefault("channel", "stable")
    if value["channel"] not in CHANNELS:
        raise InstallError(f"Unrecognized installed release channel: {target}")
    for relative, fingerprint in value["files"].items():
        path = target / relative
        if Path(relative).is_absolute() or not path.resolve().is_relative_to(target.resolve()):
            raise InstallError("Installation manifest contains an unsafe path")
        if not path.is_file() or path.is_symlink() or _hash(path) != fingerprint:
            raise InstallError(f"Installed file was modified or removed; preserve it before updating/removing: {path}")
        if any(parent.is_symlink() for parent in path.parents if parent != target and parent.is_relative_to(target)):
            raise InstallError(f"Owned file traverses a linked directory: {path}")
    return value


def _targets(project: Path, hosts: list[str]) -> list[Path]:
    project = project.resolve()
    targets = sorted({project / HOSTS[host] for host in hosts})
    for target in targets:
        if not target.resolve().is_relative_to(project):
            raise InstallError("Installation destination escapes the selected project through a link")
        if target.is_symlink() or any(parent.is_symlink() for parent in target.parents if parent != project and parent.is_relative_to(project)):
            raise InstallError("Installation destination contains a linked directory")
    return targets


def install(project: Path, hosts: list[str], *, source: Path = SOURCE,
            generation_handoff: bool | None = None, remove: bool = False,
            channel: str = "stable") -> list[dict]:
    if sys.version_info < (3, 11):
        raise InstallError("SpecViz requires Python 3.11 or later")
    project = Path(project).resolve()
    if not project.is_dir():
        raise InstallError("Select an existing project directory")
    if not hosts or any(host not in HOSTS for host in hosts):
        raise InstallError("Choose codex, claude-code, antigravity, or all")
    source = Path(source).resolve()
    try:
        release, files = validate(source, channel) if not remove else ({}, {})
    except BundleError as exc:
        raise InstallError(str(exc)) from exc
    if not remove and (not (source / "SKILL.md").is_file() or not files):
        raise InstallError("The maintained skill bundle is incomplete")
    targets = _targets(project, hosts)
    prior = {target: _owned(target) for target in targets}
    # Validate every target before mutating any selected installation.
    if not remove:
        for target in targets:
            if target.resolve() == source:
                raise InstallError("Cannot install over the maintained skill source")
            for relative in files:
                existing = target / relative
                if not existing.resolve().is_relative_to(target.resolve()) or any(parent.is_symlink() for parent in existing.parents if parent != target and parent.is_relative_to(target)):
                    raise InstallError(f"Bundle destination traverses a linked directory: {existing}")
                if existing.exists() and (prior[target] is None or relative not in prior[target]["files"]):
                    raise InstallError(f"Unowned file conflicts with the bundle: {existing}")
    results = []
    for target in targets:
        old = prior[target]
        if remove:
            if old is None:
                results.append({"path": str(target), "status": "not installed"})
                continue
            for relative in old["files"]:
                (target / relative).unlink()
            (target / MANIFEST).unlink()
            for directory in sorted((p for p in target.rglob("*") if p.is_dir() and not p.is_symlink()), key=lambda p: len(p.parts), reverse=True):
                if not any(directory.iterdir()):
                    directory.rmdir()
            if not any(target.iterdir()):
                target.rmdir()
            results.append({"path": str(target), "status": "removed owned files; unrelated files retained"})
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".specviz-stage-", dir=target.parent))
        backup = target.parent / (temporary.name + "-backup")
        try:
            if target.exists():
                shutil.copytree(target, temporary, dirs_exist_ok=True, symlinks=True)
            if old:
                for relative in old["files"]:
                    if relative not in files:
                        (temporary / relative).unlink(missing_ok=True)
            for relative, path in files.items():
                output = temporary / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, output)
            enabled = generation_handoff if generation_handoff is not None else bool(old and old.get("generation_handoff"))
            registrations = set(old.get("hosts", [])) if old else set()
            registrations.update(host for host in hosts if project / HOSTS[host] == target)
            manifest = {"owner": "specviz", "schema_version": 1, "version": release["version"],
                        "channel": channel, "source_identity": release["source_identity"],
                        "scope": "project", "hosts": sorted(registrations),
                        "generation_handoff": enabled,
                        "files": {relative: _hash(path) for relative, path in files.items()}}
            (temporary / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if target.exists():
                os.replace(target, backup)
            try:
                os.replace(temporary, target)
            except OSError:
                if backup.exists():
                    os.replace(backup, target)
                raise
            if backup.exists():
                shutil.rmtree(backup)
            results.append({"path": str(target), "status": "updated" if old else "installed",
                            "version": release["version"], "channel": channel,
                            "source_identity": release["source_identity"], "generation_handoff": enabled})
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install/update/remove SpecViz in one explicit project")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--host", choices=tuple(HOSTS) + ("all",), default="codex")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--channel", choices=CHANNELS, default="stable", help="Stable by default; beta requires explicit opt-in")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--generation-handoff", dest="generation", action="store_true")
    group.add_argument("--no-generation-handoff", dest="generation", action="store_false")
    parser.set_defaults(generation=None)
    args = parser.parse_args(argv)
    try:
        hosts = list(HOSTS) if args.host == "all" else [args.host]
        results = install(args.project, hosts, generation_handoff=args.generation, remove=args.uninstall, channel=args.channel)
    except (InstallError, OSError) as exc:
        print(f"SpecViz installation: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"python": sys.version.split()[0], "scope": "project", "installations": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
