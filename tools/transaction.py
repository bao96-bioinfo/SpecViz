"""Recoverable replacement of owned skill trees and host configuration files."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from bundle import BundleError


def remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def write_json(path: Path, value: dict) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".transaction-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class Transaction:
    """Serialize installs; restore an unfinished replacement on the next run.

    A committed journal means all replacements succeeded. Before that point,
    recovery restores backups even if interruption preceded a journal update.
    """

    def __init__(self, directory: Path):
        self.directory = directory
        self.lock = directory / "install.lock"
        self.journal = directory / "install-transaction.json"
        self.operations = []
        self.committed = False

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            self.lock.mkdir()
        except FileExistsError:
            try:
                pid = int((self.lock / "pid").read_text())
                os.kill(pid, 0)
            except ProcessLookupError:
                remove(self.lock)
                self.lock.mkdir()
            except (OSError, ValueError) as exc:
                raise BundleError("Installer lock is unavailable; another setup may be running") from exc
            else:
                raise BundleError("Another SpecViz installation is running")
        (self.lock / "pid").write_text(str(os.getpid()))
        try:
            if self.journal.exists():
                self._recover(json.loads(self.journal.read_text(encoding="utf-8")))
        except BaseException:
            remove(self.lock)
            raise
        return self

    def _recover(self, record):
        for entry in reversed(record["operations"]):
            target, stage, backup = (Path(entry[k]) for k in ("target", "stage", "backup"))
            if record.get("committed"):
                remove(backup)
            elif backup.exists():
                remove(target)
                os.replace(backup, target)
            elif not entry["existed"] and not stage.exists():
                remove(target)
            remove(stage)
        self.journal.unlink(missing_ok=True)

    def stage_tree(self, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".specviz-stage-", dir=target.parent))
        if target.exists():
            shutil.copytree(target, stage, dirs_exist_ok=True, symlinks=True)
        self.operations.append({"target": str(target), "stage": str(stage),
                                "backup": str(target.parent / (".specviz-backup-" + uuid.uuid4().hex)),
                                "existed": target.exists()})
        return stage

    def stage_file(self, target: Path, data: bytes | None) -> None:
        if any(p.is_symlink() for p in (target, *target.parents)):
            raise BundleError(f"Host configuration traverses a symbolic link: {target}")
        before = target.read_bytes() if target.exists() else None
        if before == data:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".specviz-stage-", dir=target.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data or b"")
        self.operations.append({"target": str(target), "stage": name,
                                "backup": str(target.parent / (".specviz-backup-" + uuid.uuid4().hex)),
                                "existed": before is not None, "delete": data is None})

    def commit(self):
        record = {"operations": self.operations, "committed": False}
        write_json(self.journal, record)
        try:
            for entry in self.operations:
                target, stage, backup = (Path(entry[k]) for k in ("target", "stage", "backup"))
                if entry["existed"]:
                    os.replace(target, backup)
                if entry.get("delete"):
                    stage.unlink()
                else:
                    os.replace(stage, target)
            record["committed"] = True
            write_json(self.journal, record)
            self.committed = True
        except BaseException:
            self._recover(record)
            raise
        self._recover(record)

    def __exit__(self, *exc):
        for entry in self.operations:
            remove(Path(entry["stage"]))
        remove(self.lock)

