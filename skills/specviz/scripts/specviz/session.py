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

    def save(self, inventory: dict, pages: list[str], session: str | None = None,
             page_documents: list[list[str]] | None = None, initial_page: int = 1) -> str:
        token = uuid.uuid4().hex
        payload = {"schema_version": 1, "view": token, "root": str(self.project),
                   "snapshot": inventory["snapshot"], "pages": pages,
                   "sources": [{"id": doc["id"], "absolute_path": doc["absolute_path"], "hash": doc["hash"]}
                               for doc in inventory["documents"]],
                   "selection": [doc["id"] for doc in inventory["documents"]],
                   "visible": inventory.get("scope", []) + inventory.get("context", [])}
        if page_documents is not None:
            payload["document_pages"] = {
                identity: [index for index, refs in enumerate(page_documents, 1) if identity in refs]
                for identity in payload["selection"] if any(identity in refs for refs in page_documents)}
            payload["delivered_pages"] = [initial_page]
            payload["conversation"] = digest(session) if session else None
            self._visibility(payload)
        self._write(self.directory / f"{token}.json", payload)
        if session:
            self._write(self.directory / f"session-{digest(session)}.json", {"view": token})
        return token

    def load(self, token: str) -> dict:
        if token and token.startswith("b-"):
            raise ValidationError("This is a retired beta view; request a fresh stable overview. Its saved record and implementation evidence are retained.")
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

    @staticmethod
    def _visibility(payload: dict) -> None:
        delivered = set(payload["delivered_pages"])
        payload["visible"] = [identity for identity, pages in payload["document_pages"].items()
                              if pages and set(pages).issubset(delivered)]

    def deliver(self, token: str, page: int, session: str | None = None) -> dict:
        payload = self.load(token)
        if not 1 <= page <= len(payload["pages"]):
            raise ValidationError("No such continuation page")
        if "document_pages" in payload:
            expected = payload.get("conversation")
            if expected is not None and expected != (digest(session) if session else None):
                raise ValidationError("Continuation belongs to another conversation; use the original --session")
            payload["delivered_pages"] = sorted(set(payload["delivered_pages"]) | {page})
            self._visibility(payload)
            self._write(self.directory / f"{token}.json", payload)
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
                    raise ValidationError(f"File {selection} has not been exposed in this conversation; continue the file key or select a path")
                result.append(paths[index])
            else:
                result.append(selection)
        return result
