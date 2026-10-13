"""Conversation-specific selection and snapshot-bound text continuation."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path

from .core import ValidationError, digest, project_identity


class ViewStore:
    def __init__(self, project: Path, state_dir: Path):
        self.project = Path(project).resolve()
        state_dir = Path(state_dir).resolve()
        if state_dir.is_relative_to(self.project):
            raise ValidationError("View state must be outside the project")
        self.directory = state_dir / "views" / project_identity(self.project)

    def _write(self, path: Path, payload: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, ensure_ascii=False)
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)

    def save(self, inventory: dict, pages: list[str], session: str | None = None) -> str:
        token = uuid.uuid4().hex
        payload = {"schema_version": 1, "view": token, "root": str(self.project),
                   "snapshot": inventory["snapshot"], "pages": pages,
                   "sources": [{"id": doc["id"], "absolute_path": doc["absolute_path"], "hash": doc["hash"]}
                               for doc in inventory["documents"]],
                   "selection": [doc["id"] for doc in inventory["documents"]],
                   "visible": inventory.get("scope", []) + inventory.get("context", [])}
        self._write(self.directory / f"{token}.json", payload)
        if session:
            self._write(self.directory / f"session-{digest(session)}.json", {"view": token})
        return token

    def load(self, token: str) -> dict:
        if not token or any(c not in "0123456789abcdef" for c in token) or len(token) != 32:
            raise ValidationError("Invalid view identity; request a new overview")
        try:
            payload = json.loads((self.directory / f"{token}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValidationError("Displayed inventory is unavailable; request a new overview") from exc
        if payload.get("root") != str(self.project) or payload.get("schema_version") != 1:
            raise ValidationError("Displayed inventory belongs to a different project or schema")
        for source in payload["sources"]:
            try:
                if digest(Path(source["absolute_path"]).read_bytes()) != source["hash"]:
                    raise ValidationError("Displayed sources changed; request a refreshed overview")
            except OSError as exc:
                raise ValidationError("Displayed source moved or became unavailable; refresh the overview") from exc
        return payload

    def latest(self, session: str) -> dict:
        try:
            value = json.loads((self.directory / f"session-{digest(session)}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValidationError("No file map in this conversation; select files by path or request overview") from exc
        return self.load(value["view"])

    def select(self, selections: list[str], session: str) -> list[str]:
        payload = self.latest(session)
        paths = payload["selection"]
        result = []
        for selection in selections:
            if selection.isdecimal():
                index = int(selection) - 1
                if not 0 <= index < len(paths):
                    raise ValidationError(f"No file {selection} in the displayed inventory")
                if paths[index] not in payload.get("visible", paths):
                    raise ValidationError(f"File {selection} was outside the latest displayed map; select a path or refresh overview")
                result.append(paths[index])
            else:
                result.append(selection)
        return result
