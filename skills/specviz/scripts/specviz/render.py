"""Deterministic in-chat text views; this module never reads or modifies files."""

from __future__ import annotations

import re
from typing import Any

from .core import default_items


from .text import clean as _clean, display_width, wrap_text


class _Writer:
    def __init__(self, width: int):
        if width < 24:
            raise ValueError("Text views require a width of at least 24 columns.")
        self.width = width
        self.lines: list[str] = []

    def add(self, text: Any = "", prefix: str = "", continuation: str | None = None) -> None:
        continuation = " " * display_width(prefix) if continuation is None else continuation
        available = self.width - max(display_width(prefix), display_width(continuation))
        for index, line in enumerate(wrap_text(text, available)):
            self.lines.append(((prefix if index == 0 else continuation) + line).rstrip())

    def raw(self, line: str = "") -> None:
        self.add(line)

    def result(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"


def _snapshot(inventory: dict[str, Any]) -> str:
    snapshot = inventory.get("snapshot", "unavailable")
    if isinstance(snapshot, dict):
        return str(snapshot.get("id", snapshot.get("hash", "unavailable")))
    return str(snapshot)


def _documents(inventory: dict[str, Any], document_ids: list[str] | None = None) -> list[dict]:
    documents = inventory.get("documents", [])
    if document_ids is None:
        document_ids = inventory.get("scope")
    if document_ids is None:
        return list(documents)
    selected = set(document_ids)
    return [doc for doc in documents if doc["id"] in selected or doc["path"] in selected]


def _model_documents(model: dict | None) -> dict[str, dict]:
    return {doc["id"]: doc for doc in (model or {}).get("documents", [])}


def _purpose(document: dict, interpreted: dict | None = None) -> str:
    return str((interpreted or {}).get("purpose") or document.get("purpose") or "Purpose unspecified")


def _groups(inventory: dict, documents: list[dict]) -> list[tuple[dict, list[dict]]]:
    ordered = list(inventory.get("groups", []))
    known = {str(group["id"]) for group in ordered}
    for document in documents:
        identity = str(document.get("group") or "Other specifications")
        if identity not in known:
            ordered.append({"id": identity, "label": identity, "purpose": "Purpose unspecified"})
            known.add(identity)
    return [(group, [doc for doc in documents if str(doc.get("group") or "Other specifications") == str(group["id"])])
            for group in ordered
            if any(str(doc.get("group") or "Other specifications") == str(group["id"]) for doc in documents)]


def _numbers(inventory: dict) -> dict[str, int]:
    return {document["id"]: index for index, document in enumerate(inventory.get("documents", []), 1)}


def _file_count(count: int) -> str:
    return f"{count} file" + ("" if count == 1 else "s")


def render_overview(inventory: dict, model: dict | None = None, detailed: bool = False,
                    width: int = 80) -> str:
    """Return the structured overview as ordinary fixed-width text."""
    from .views import overview_view
    return overview_view(inventory, model, detailed, width).render()


def _items(document: dict, interpreted: dict | None) -> list[dict]:
    if interpreted is not None:
        result = list(interpreted.get("items", []))
        blocks = {block["id"]: block for block in document.get("blocks", [])}
        for source in interpreted.get("unresolved", []):
            block = blocks.get(source)
            label = " / ".join(block.get("heading", [])) if block else "Unknown source section"
            result.append({"id": source, "label": label or "Uninterpreted source", "kind": "unresolved",
                           "sources": [source], "notes": [block["text"]] if block else []})
        return result
    return default_items(document)


def _source_refs(document: dict, item: dict) -> list[str]:
    blocks = {block["id"]: block for block in document.get("blocks", [])}
    references = []
    spans: list[dict] = []
    for source in item.get("sources", []):
        block = blocks.get(source)
        if block is None:
            references.append(f"{document['path']}: unresolved source {source}")
            continue
        spans.append(dict(block))
    merged: list[dict] = []
    for block in sorted(spans, key=lambda value: value.get("start_line", 0)):
        if merged and block.get("heading") == merged[-1].get("heading") and block.get("start_line", 0) <= merged[-1].get("end_line", -3) + 2:
            merged[-1]["end_line"] = max(block.get("end_line", 0), merged[-1].get("end_line", 0))
        else:
            merged.append(block)
    for block in merged:
        span = str(block.get("start_line", "?"))
        if block.get("end_line") != block.get("start_line"):
            span += "-" + str(block.get("end_line", "?"))
        heading = " / ".join(str(value) for value in block.get("heading", []))
        references.append(f"lines {span}" + (f" - {heading}" if heading else ""))
    return references


def _item_notes(document: dict, item: dict) -> list[str]:
    if item.get("notes"):
        return [str(note) for note in item["notes"]]
    blocks = {block["id"]: block for block in document.get("blocks", [])}
    return [str(blocks[source]["text"]) for source in item.get("sources", []) if source in blocks]


def render_show(inventory: dict, document_ids: list[str] | None = None, model: dict | None = None,
                detailed: bool = False, width: int = 80) -> str:
    """Return the structured selected-file view as ordinary fixed-width text."""
    from .views import show_view
    return show_view(inventory, document_ids, model, detailed, width).render()


def _active_change(row: dict) -> bool:
    return row.get("difference") not in {"unchanged", "documentation-only"} or row.get("status") in {
        "unknown", "stale", "contradicted", "not found", "unclear", "partial", "code partial", "task progress"}


def _fact(writer: _Writer, label: str, value: Any, prefix: str = "|   ") -> None:
    if value not in (None, "", [], {}):
        writer.add(label + ": " + _clean(value), prefix, prefix)


def _completion(writer: _Writer, evidence: Any) -> None:
    if not isinstance(evidence, dict):
        _fact(writer, "Completion evidence", evidence or "Unavailable")
        return
    writer.add("Completion evidence:", "|   ")
    prefix = "|     "
    for key, label in (("origin", "Report origin"), ("framework", "Workflow"), ("recorded_at", "Recorded"),
                       ("event_id", "Report identifier"), ("round_id", "Implementation round")):
        value = evidence.get(key)
        if key == "origin" and isinstance(value, dict):
            value = str(value.get("source") or "Source unspecified") + " (" + str(value.get("kind") or "Origin unspecified") + ")"
        _fact(writer, label, value, prefix)
    coverage = evidence.get("coverage")
    if isinstance(coverage, dict):
        _fact(writer, "Coverage", coverage.get("status"), prefix)
        _fact(writer, "Supported and outstanding parts", coverage.get("details"), prefix)
        _fact(writer, "Evidence limit", coverage.get("limitation"), prefix)
        if coverage.get("version_bound") is False:
            _fact(writer, "Source version binding", "Unavailable; reported work cannot establish complete requirement compliance.", prefix)
    else:
        _fact(writer, "Coverage", coverage, prefix)
    specification = evidence.get("specification", {})
    if isinstance(specification, dict):
        _fact(writer, "Implemented specification", specification.get("path"), prefix)
        _fact(writer, "Specification version", specification.get("hash"), prefix)
    implementation = evidence.get("implementation", {})
    if isinstance(implementation, dict):
        _fact(writer, "Code revision", implementation.get("revision"), prefix)
        if isinstance(implementation.get("files"), (dict, list)):
            _fact(writer, "Code identity", f"{len(implementation['files'])} bound source files; " +
                  ("conservative project manifest" if implementation.get("complete_manifest") else "scoped source manifest"), prefix)
        _fact(writer, "Code identity limit", implementation.get("limitation"), prefix)
    fingerprints = evidence.get("fingerprints", {})
    if isinstance(fingerprints, dict):
        _fact(writer, "Evidence freshness", fingerprints.get("status"), prefix)
        _fact(writer, "Freshness explanation", fingerprints.get("reason"), prefix)


def _brief(value: Any, limit: int = 180) -> str:
    """Bound an explanatory summary, explicitly pointing to unabridged detail."""
    summary = " ".join(_clean(value).split())
    if len(summary) <= limit:
        return summary
    shortened = summary[:limit].rsplit(" ", 1)[0] or summary[:limit]
    return shortened + " ... (expand --detailed)"


def _verification(writer: _Writer, verification: Any, historical: bool = False, detailed: bool = True) -> None:
    label = "Earlier behavior verification" if historical else "Verification"
    if not verification:
        _fact(writer, label, "Unavailable; passing checks are not established.")
    elif isinstance(verification, dict):
        if verification.get("executed") is False:
            _fact(writer, label, "Checks were not executed; passing results are not established.")
        elif verification.get("executed") is True:
            _fact(writer, label, "Executed checks reported; " + ("results follow." if detailed else "commands and results available with --detailed."))
        else:
            _fact(writer, label, "Reported check information; execution provenance is unspecified.")
        if detailed:
            for key, label in (("check", "Check"), ("result", "Reported result"), ("checks", "Reported checks"),
                               ("origin", "Verification origin"), ("reason", "Verification explanation")):
                _fact(writer, label, verification.get(key))
    else:
        _fact(writer, label, verification if detailed else "Reported verification information; expand --detailed for its source and limits.")


def _inspection(writer: _Writer, inspection: Any, detailed: bool = True, reason_shown: str = "") -> None:
    if not isinstance(inspection, dict):
        _fact(writer, "Code inspection", inspection if detailed else _brief(inspection))
        return
    finding = inspection.get("finding", inspection)
    record = inspection.get("record", {})
    if not detailed:
        freshness = record.get("fingerprints", {})
        stale = isinstance(freshness, dict) and freshness.get("status") not in {None, "current"}
        _fact(writer, "Code finding", str(finding.get("status") or "unclear") + (" (stale; current support unconfirmed)" if stale else ""))
        for key, label in (("reason", "Code explanation"), ("observation", "Code observation"),
                           ("supported", "Supported portions"), ("outstanding", "Outstanding portions"),
                           ("uninspected", "Uninspected scope")):
            value = finding.get(key)
            if value and not (key == "reason" and str(value) in reason_shown):
                _fact(writer, label, _brief(value))
        if record.get("complete") is False:
            _fact(writer, "Inspection scope", "Incomplete; remaining behavior needs inspection.")
        _fact(writer, "Inspection limit", "Observation only; workflow rounds unchanged and tests were not executed.")
        return
    writer.add("Code inspection:", "|   ")
    prefix = "|     "
    for key, label in (("status", "Finding"), ("reason", "Explanation"), ("observation", "Observation"),
                       ("supported", "Supported portions"), ("outstanding", "Outstanding portions"),
                       ("uninspected", "Uninspected scope"), ("source", "Source")):
        _fact(writer, label, finding.get(key), prefix)
    for location in finding.get("locations", []):
        if isinstance(location, dict):
            _fact(writer, "Inspected source", str(location.get("path", "Unspecified")) + ":" + str(location.get("line", "?")), prefix)
    if record.get("complete") is False:
        _fact(writer, "Inspection scope", "Incomplete; continue inspection of the remaining behavior.", prefix)
    if record.get("inspection_id"):
        _fact(writer, "Inspection identifier", record["inspection_id"], prefix)
    _fact(writer, "Inspection freshness", record.get("fingerprints"), prefix)
    tests = finding.get("tests")
    if tests:
        _fact(writer, "Test evidence", "Definitions were inspected; tests were not executed by this inspection.", prefix)
        if isinstance(tests, dict):
            for key, value in tests.items():
                if key != "executed":
                    _fact(writer, "Test " + key.replace("_", " "), value, prefix)
    writer.add("Inspection is a separate observation; it does not complete a workflow round.", "|   ", "|   ")


def _evidence_status(row: dict) -> str:
    """Say which behavior an old report covers when the requested behavior differs."""
    status = str(row.get("status") or "unknown")
    report_difference = row.get("report_difference", row.get("difference"))
    earlier = report_difference not in {"unchanged", "documentation-only"}
    if status == "reported implemented":
        return "Earlier behavior reported implemented" if earlier else "Requested behavior reported implemented"
    if status == "partial":
        return "Earlier behavior partly reported implemented" if earlier else "Requested behavior partly reported implemented"
    return {"code supported": "Current code supports requested behavior",
            "code partial": "Current code supports part of requested behavior",
            "contradicted": "Current code contradicts requested behavior",
            "not found": "Requested behavior not located; absence is not proven",
            "unclear": "Current implementation remains unclear",
            "stale": "Earlier implementation report is stale; current behavior is uncertain",
            "unknown": "Implementation unknown",
            "task progress": "Task progress reported; requirement implementation remains unknown"}.get(status, status)


def _comparison_row(writer: _Writer, row: dict, item_labels: dict, detailed: bool) -> None:
    marker = "[changed] " if row.get("difference") not in {"unchanged", "documentation-only", "unresolved", "source-unavailable"} else ("[attention] " if _active_change(row) else "")
    requirement_id = row.get("requirement_id") or "Unidentified requirement"
    writer.add(f"{marker}{item_labels.get(requirement_id) or row.get('label') or requirement_id}", "+-- ", "|   ")
    code_matches = row.get("difference_basis") == "current code inspection" and row.get("status") == "code supported"
    writer.add("Difference vs inspected code: none identified" if code_matches else
               "Difference: " + str(row.get("difference") or "unresolved"), "|   ", "|   ")
    writer.add("Evidence status: " + _evidence_status(row), "|   ", "|   ")
    if row.get("reason"):
        writer.add(row["reason"] if detailed else _brief(row["reason"]), "|   ", "|   ")
    if detailed:
        writer.add("Requested: " + str(row.get("requested") or "Unspecified"), "|   ", "|   ")
        earlier = row.get("report_difference", row.get("difference")) not in {"unchanged", "documentation-only"}
        writer.add(("Earlier reported behavior: " if earlier else "Reported implementation reference: ") +
                   str(row.get("implemented") or "Unavailable"), "|   ", "|   ")
    if row.get("difference_basis") == "current code inspection":
        if not row.get("evidence"):
            writer.add("Workflow report reference: unavailable; current findings come from code inspection.", "|   ", "|   ")
        elif row.get("report_difference") not in {None, "unchanged", "documentation-only"}:
            writer.add("Earlier report comparison: " + str(row["report_difference"]) + "; retained separately from the current code finding.", "|   ", "|   ")
    if row.get("temporal_order_uncertain"):
        writer.add("Workflow report order is uncertain; no candidate is confirmed as the latest implementation.", "|   ", "|   ")
        if detailed:
            _fact(writer, "Candidate report comparison", row.get("candidate_report_difference"))
            for alternative in row.get("report_alternatives", []):
                writer.add("Alternative earlier report candidate:", "|   ")
                _fact(writer, "Reported behavior", alternative.get("implemented"))
                _completion(writer, alternative)
    if detailed:
        _completion(writer, row.get("evidence"))
        if row.get("sources"):
            writer.add("Source blocks: " + ", ".join(str(value) for value in row["sources"]), "|   ", "|   ")
        if item_labels.get(requirement_id) or row.get("label"):
            writer.add("Source identifier: " + str(requirement_id), "|   ", "|   ")
    historical_verification = bool(row.get("implemented")) and (
        row.get("report_difference", row.get("difference")) not in {"unchanged", "documentation-only"}
        or row.get("report_status", row.get("status")) == "stale")
    _verification(writer, row.get("verification"), historical=historical_verification, detailed=detailed)
    if row.get("inspection"):
        _inspection(writer, row["inspection"], detailed=detailed, reason_shown=_brief(row.get("reason", "")))


def render_changes(inventory: dict, comparison: dict, model: dict | None = None,
                   detailed: bool = False, width: int = 80) -> str:
    """Render boxed changes while preserving separate evidence sources."""
    from .views import changes_view
    return changes_view(inventory, comparison, model, detailed, width).render()


def split_pages(text: str, snapshot: str, max_lines: int = 100, width: int = 80) -> list[str]:
    """Produce complete explicit continuation chunks tied to one immutable snapshot."""
    if max_lines < 8:
        raise ValueError("A continuation page requires at least 8 content lines.")
    lines = text.rstrip("\n").split("\n")
    chunks = [lines[index:index + max_lines] for index in range(0, len(lines), max_lines)] or [[]]
    if len(chunks) == 1:
        return [text]
    result = []
    for index, chunk in enumerate(chunks):
        writer = _Writer(width)
        writer.add(f"Part {index + 1} of {len(chunks)}; source snapshot: {snapshot}")
        writer.raw()
        writer.lines.extend(chunk)
        writer.raw()
        remaining = len(lines) - min((index + 1) * max_lines, len(lines))
        if remaining:
            remaining_lines = lines[(index + 1) * max_lines:]
            remaining_headers = [line for line in remaining_lines if line.startswith("File [")]
            if not remaining_headers:
                remaining_headers = [line.lstrip("| ") for line in remaining_lines
                                     if line.lstrip("| ").startswith("+-- [") or re.match(r"^\[\d+\] ", line)]
            writer.add(f"{remaining} content lines remain. Continue with this snapshot and part {index + 2}.")
            if remaining_headers:
                listed = remaining_headers[:4]
                suffix = f"; and {len(remaining_headers) - 4} further file sections" if len(remaining_headers) > 4 else ""
                writer.add("Remaining files: " + "; ".join(listed) + suffix)
        else:
            writer.add("Complete: all selected content has been delivered.")
        result.append(writer.result())
    return result
