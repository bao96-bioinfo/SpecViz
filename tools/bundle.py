"""Release identity shared by local installation and reproducible packaging."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

RELEASE = "release.json"
INSTALL = ".specviz-install.json"
CHANNELS = ("stable", "beta")


class BundleError(ValueError):
    pass


def source_files(source: Path) -> dict[str, Path]:
    result = {}
    for path in sorted(source.rglob("*")):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"} or path.name == INSTALL:
            continue
        if path.is_symlink():
            raise BundleError("Release sources cannot contain symbolic links")
        if path.is_file():
            result[path.relative_to(source).as_posix()] = path
    return result


def fingerprint(files: dict[str, Path]) -> dict[str, str]:
    return {name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in files.items() if name != RELEASE}


def identity(channel: str, version: str, files: dict[str, str]) -> str:
    value = json.dumps({"channel": channel, "version": version, "files": files},
                       sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(value).hexdigest()


def check_version(channel: str, version: str) -> None:
    pattern = r"\d+\.\d+\.\d+" + (r"-beta\.\d+" if channel == "beta" else "")
    if channel not in CHANNELS or not isinstance(version, str) or not re.fullmatch(pattern, version):
        raise BundleError("Release version must match its stable or beta channel")


def seal(source: Path, channel: str, version: str) -> dict:
    """Maintainer-only operation; installers never rewrite release identity."""
    check_version(channel, version)
    files = fingerprint(source_files(source))
    if "SKILL.md" not in files:
        raise BundleError("The skill bundle is incomplete")
    value = {"schema_version": 1, "channel": channel, "version": version,
             "source_identity": identity(channel, version, files), "files": files}
    (source / RELEASE).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def validate(source: Path, channel: str = "stable") -> tuple[dict, dict[str, Path]]:
    if channel not in CHANNELS:
        raise BundleError("Choose the stable or beta release channel")
    files = source_files(source)
    try:
        value = json.loads((source / RELEASE).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError("Release metadata is missing or unreadable; use a complete stable or beta distribution") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise BundleError("Invalid release metadata")
    check_version(value.get("channel"), value.get("version"))
    if value["channel"] != channel:
        raise BundleError(f"Requested {channel}, but this source is {value['channel']}. "
                          f"Use the {channel} checkout or release bundle; beta requires --channel beta.")
    hashes = fingerprint(files)
    if "SKILL.md" not in hashes or hashes != value.get("files"):
        raise BundleError("Release content differs from its recorded source identity; use a complete distribution")
    if value.get("source_identity") != identity(channel, value["version"], hashes):
        raise BundleError("Release channel, version, and source identity disagree")
    version_file = source / "scripts/specviz/__init__.py"
    if version_file.is_file():
        match = re.search(r'^__version__\s*=\s*[\"\']([^\"\']+)[\"\']', version_file.read_text(encoding="utf-8"), re.M)
        if not match or match[1] != value["version"]:
            raise BundleError("Bundled helper version differs from release metadata")
    return value, files
