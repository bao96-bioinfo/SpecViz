"""Validate observational findings against the files actually inspected."""

from __future__ import annotations

from pathlib import Path

from .core import ValidationError, default_items, digest, require_version
from .comparison import comparison_items

STATUSES = {"supported", "partial", "contradicted", "not-found", "unclear"}


def validate_inspection(record: dict, inventory: dict, model: dict | None = None) -> dict:
    require_version(record)
    if record.get("observational") is not True or record.get("tests_executed") is not False:
        raise ValidationError("Inspection must be observational; tests are not executed")
    if not isinstance(record.get("inspection_id"), str) or not record["inspection_id"]:
        raise ValidationError("Inspection needs a unique inspection_id")
    if not isinstance(record.get("complete"), bool):
        raise ValidationError("Inspection must declare whether the selected scope is complete")
    root = Path(inventory["project"]["root"]).resolve()
    documents = {doc["id"]: doc for doc in inventory["documents"]}
    scope = record.get("scope")
    if not isinstance(scope, list) or not scope or not set(scope) <= set(inventory["scope"]):
        raise ValidationError("Inspection scope must name selected documents")
    if record["complete"] and set(scope) != set(inventory["scope"]):
        raise ValidationError("Complete inspection must cover the selected scope")
    specifications = record.get("specifications", [])
    hashes = {item.get("path"): item.get("hash") for item in specifications}
    if len(hashes) != len(specifications) or any(hashes.get(identity) != documents[identity]["hash"] for identity in scope):
        raise ValidationError("Inspection specification fingerprints are missing or stale")
    implementation = record.get("implementation", {})
    files = implementation.get("files")
    if not isinstance(files, dict) or not files:
        raise ValidationError("Inspection must identify the files it actually inspected")
    for path, fingerprint in files.items():
        source = (root / path).resolve()
        if not source.is_relative_to(root):
            raise ValidationError("Inspection file is outside the selected project")
        if not source.is_file() or digest(source.read_bytes()) != fingerprint:
            raise ValidationError(f"Inspected code changed or is unavailable: {path}")
    interpreted = {doc["id"]: doc for doc in (model or {}).get("documents", [])}
    seen: set[tuple[str, str]] = set()
    findings = record.get("findings")
    if not isinstance(findings, list):
        raise ValidationError("Inspection findings must be a list")
    for finding in findings:
        document_id = finding.get("document")
        if document_id not in scope:
            raise ValidationError("Finding refers to a document outside the inspection scope")
        items = comparison_items(documents[document_id], interpreted.get(document_id))
        ids = {item["id"] for item in items}
        identity = (document_id, finding.get("requirement_id"))
        if identity[1] not in ids or identity in seen:
            raise ValidationError("Finding has an unknown or duplicate requirement identity")
        seen.add(identity)
        if finding.get("status") not in STATUSES or not isinstance(finding.get("reason"), str) or not finding["reason"].strip():
            raise ValidationError("Finding requires a supported status and explanation")
        if finding.get("tests", {}).get("executed", False):
            raise ValidationError("Reading tests does not constitute execution")
        if finding.get("status") == "supported" and finding.get("uninspected"):
            raise ValidationError("Uninspected behavior cannot be labeled fully supported")
        locations = finding.get("locations", [])
        if not locations and finding["status"] in {"supported", "partial", "contradicted"}:
            raise ValidationError("Positive or contrary code evidence needs source locations")
        for location in locations:
            if location.get("path") not in files:
                raise ValidationError("Location refers to code not bound to the inspection")
            line = location.get("line")
            if not isinstance(line, int) or isinstance(line, bool) or line < 1:
                raise ValidationError("Inspection line numbers must be positive integers")
            content = (root / location["path"]).read_text(encoding="utf-8")
            if line > len(content.splitlines()):
                raise ValidationError("Inspection line is outside its source file")
    if record["complete"]:
        expected = set()
        for identity in scope:
            items = comparison_items(documents[identity], interpreted.get(identity))
            expected.update((identity, item["id"]) for item in items)
        if expected - seen:
            raise ValidationError("Complete inspection omits selected requirements")
    return record
