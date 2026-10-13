"""Immutable source snapshots and validated, source-backed interpretations."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import SCHEMA_VERSION


class ValidationError(ValueError):
    """A submitted record does not satisfy its documented contract."""


def digest(value: str | bytes) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def project_identity(root: Path | str) -> str:
    root = Path(root).resolve()
    git = root / ".git"
    identity = str(root)
    if git.is_file():
        identity += "\n" + git.read_text(encoding="utf-8").strip()
    return digest(identity)


def source_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return "external::" + path.resolve().as_posix()


def _stat_identity(stat: object) -> tuple:
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def read_stable(path: Path) -> bytes:
    """Read one immutable version or fail rather than mixing edited versions."""
    for _ in range(3):
        before = path.stat()
        with path.open("rb") as stream:
            data = stream.read()
        after = path.stat()
        if _stat_identity(before) == _stat_identity(after) and len(data) == after.st_size:
            return data
    raise ValidationError(f"Source changed while reading: {path}; retry the view")


def parse_blocks(text: str, document_id: str) -> list[dict]:
    """Preserve every nonblank Markdown block, including unfamiliar constructs."""
    lines = text.splitlines()
    blocks: list[dict] = []
    headings: list[tuple[int, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index].lstrip("\ufeff") if index == 0 else lines[index]
        if not line.strip():
            index += 1
            continue
        start = index
        heading = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        setext = index + 1 < len(lines) and re.fullmatch(r" {0,3}(?:=+|-+)\s*", lines[index + 1])
        if heading:
            level, label = len(heading[1]), heading[2]
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, label))
            kind = "heading"
            index += 1
        elif fence:
            marker = fence[1]
            kind = "code"
            index += 1
            closing = re.compile(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$")
            while index < len(lines):
                ended = bool(closing.match(lines[index]))
                index += 1
                if ended:
                    break
        elif setext and line.strip():
            level = 1 if lines[index + 1].lstrip().startswith("=") else 2
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, line.strip()))
            kind = "heading"
            index += 2
        else:
            list_item = re.match(r"^(\s*)(?:[-+*]|\d+[.)])\s+", line)
            kind = "list" if list_item else "paragraph"
            if "|" in line and index + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[index + 1]):
                kind = "table"
            if line.lstrip().startswith(("<", ":::")):
                kind = "unknown"
            index += 1
            while index < len(lines) and lines[index].strip():
                if re.match(r"^ {0,3}(?:#{1,6}\s|`{3,}|~{3,})", lines[index]):
                    break
                next_item = re.match(r"^(\s*)(?:[-+*]|\d+[.)])\s+", lines[index])
                if list_item and next_item and len(next_item[1]) <= len(list_item[1]):
                    break
                index += 1
        blocks.append({
            "id": f"{document_id}:L{start + 1}-{index}",
            "kind": kind,
            "text": "\n".join(lines[start:index]),
            "start_line": start + 1,
            "end_line": index,
            "heading": [label for _, label in headings],
        })
    return blocks


def snapshot_file(path: Path | str, root: Path | str) -> dict:
    path, root = Path(path).resolve(), Path(root).resolve()
    data = read_stable(path)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"Source is not UTF-8 text: {path}") from exc
    identity = source_path(path, root)
    blocks = parse_blocks(text, identity)
    title = next((b["heading"][-1] for b in blocks if b["kind"] == "heading"), path.name)
    purpose = next((b["text"].replace("\n", " ") for b in blocks if b["kind"] == "paragraph"), "Purpose unspecified")
    return {"id": identity, "path": identity, "absolute_path": str(path), "hash": digest(data),
            "text": text, "blocks": blocks, "title": title, "purpose": purpose}


def default_items(document: dict) -> list[dict]:
    """Uninterpreted section items preserve exact source text and coverage."""
    items: list[dict] = []
    current = None
    occurrences: dict[str, int] = {}
    for block in document["blocks"]:
        if current is None or block["kind"] == "heading":
            label = " / ".join(block["heading"]) or "Introduction"
            occurrence = occurrences.get(label, 0) + 1
            occurrences[label] = occurrence
            slug = re.sub(r"[^\w-]+", "-", label.casefold()).strip("-") or "introduction"
            current = {"id": f"{document['id']}#{slug}:{occurrence}", "label": label,
                       "kind": "unknown", "sources": [], "notes": []}
            items.append(current)
        current["sources"].append(block["id"])
        if block["kind"] != "heading":
            current["notes"].append(block["text"])
    return items


def require_version(record: dict) -> None:
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(f"Expected schema_version {SCHEMA_VERSION}")


def validate_inventory(inventory: dict) -> dict:
    require_version(inventory)
    if not isinstance(inventory.get("project"), dict) or not inventory["project"].get("root"):
        raise ValidationError("Inventory needs an identified project")
    documents = inventory.get("documents")
    if not isinstance(documents, list):
        raise ValidationError("Inventory documents must be a list")
    identities = [doc.get("id") for doc in documents]
    if any(not isinstance(identity, str) for identity in identities) or len(set(identities)) != len(identities):
        raise ValidationError("Document identities must be unique strings")
    for doc in documents:
        if not all(key in doc for key in ("path", "hash", "text", "blocks")):
            raise ValidationError("Document lacks a source snapshot")
    for relation in inventory.get("relationships", []):
        if relation.get("type") not in {"containment", "reference", "workflow", "reading"}:
            raise ValidationError("Unsupported relationship type")
        allowed_from = identities + ([group["id"] for group in inventory.get("groups", [])] if relation.get("type") == "containment" else [])
        if relation.get("from") not in allowed_from:
            raise ValidationError("Relationship starts at an unknown document")
        if relation.get("to") not in identities and not relation.get("unresolved"):
            raise ValidationError("Relationship target is missing without an unresolved marker")
    for identity in inventory.get("scope", []) + inventory.get("context", []):
        if identity not in identities:
            raise ValidationError("Scope refers to an unknown document")
    return inventory


def validate_model(model: dict, inventory: dict) -> dict:
    require_version(model)
    if model.get("snapshot") != inventory.get("snapshot"):
        raise ValidationError("Interpretation is for a different source snapshot; refresh it")
    known = {doc["id"]: doc for doc in inventory["documents"]}
    seen: set[str] = set()
    if not isinstance(model.get("documents"), list):
        raise ValidationError("Interpretation documents must be a list")
    for doc in model["documents"]:
        identity = doc.get("id")
        if identity not in known or identity in seen:
            raise ValidationError("Interpretation contains an unknown or duplicate document")
        seen.add(identity)
        if doc.get("layout", "tree") not in {"tree", "flow", "interaction", "rules"}:
            raise ValidationError("Unsupported text layout")
        if not isinstance(doc.get("purpose"), str) or not doc["purpose"].strip():
            raise ValidationError("Interpretation needs a plain-language document purpose")
        sources = {b["id"] for b in known[identity]["blocks"]}
        substantive = {b["id"] for b in known[identity]["blocks"] if b["kind"] != "heading"}
        covered: set[str] = set()
        item_ids: set[str] = set()
        for item in doc.get("items", []):
            if not isinstance(item.get("id"), str) or item["id"] in item_ids:
                raise ValidationError("Semantic item identities must be unique strings")
            item_ids.add(item["id"])
            if not isinstance(item.get("label"), str) or not item["label"].strip():
                raise ValidationError("Semantic item needs a readable label")
            references = item.get("sources")
            if not isinstance(references, list) or not references or not set(references) <= sources:
                raise ValidationError("Semantic item has missing or invented source references")
            if not isinstance(item.get("notes", []), list) or any(not isinstance(n, str) for n in item.get("notes", [])):
                raise ValidationError("Item notes must be text")
            covered.update(references)
        unresolved = doc.get("unresolved", [])
        if not isinstance(unresolved, list) or not set(unresolved) <= sources:
            raise ValidationError("Unknown unresolved source block")
        covered.update(unresolved)
        if substantive - covered:
            raise ValidationError("Interpretation omits substantive blocks: " + ", ".join(sorted(substantive - covered)))
        for relation in doc.get("relationships", []):
            if relation.get("from") not in item_ids or relation.get("to") not in item_ids:
                raise ValidationError("Interpretation relation refers to an unknown item")
            if relation.get("type") not in {"containment", "reference", "workflow", "reading", "interaction", "condition"}:
                raise ValidationError("Unsupported semantic relationship type")
    if set(inventory.get("scope", known)) - seen:
        raise ValidationError("Interpretation omits selected documents")
    return model
