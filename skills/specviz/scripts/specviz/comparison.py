"""Compare requested source versions with scoped, provenance-bound evidence."""
from __future__ import annotations

import re
from pathlib import Path

from .core import default_items, parse_blocks, validate_model, digest, read_stable
from .discovery import specification_paths
from .evidence import EvidenceError, EvidenceStore


def requested_text(item: dict, document: dict) -> str:
    """Use source content for comparison; a display paraphrase is not a baseline."""
    references = set(item.get("sources", []))
    blocks = document["blocks"]
    selected = [index for index, block in enumerate(blocks) if block["id"] in references]
    lines = document["text"].splitlines(keepends=True)
    groups = []
    for index in selected:
        if groups and groups[-1][-1] == index - 1:
            groups[-1].append(index)
        else:
            groups.append([index])
    return "\n\n".join("".join(lines[blocks[group[0]]["start_line"] - 1:blocks[group[-1]]["end_line"]]).rstrip("\r\n")
                       for group in groups)


def comparison_items(document: dict, interpreted: dict | None = None) -> list[dict]:
    """Shared scope for comparison and complete-inspection coverage validation."""
    substantive = {block["id"] for block in document["blocks"] if block["kind"] != "heading"}
    behavior_kinds = {"requirement", "goal", "rule", "constraint", "decision", "task", "behavior"}
    return [item for item in (interpreted or {}).get("items", default_items(document))
            if set(item["sources"]) & substantive or item.get("kind") in behavior_kinds]


def _format_normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _prose_whitespace_equivalent(left: str, right: str) -> bool:
    """Recognize only plain prose wrapping with unchanged block structure.

    Whitespace in literals, nested obligations, code, tables, and unfamiliar
    constructs may be semantic. Do not silently normalize those into equivalence.
    """
    structures = []
    for text in (left, right):
        if "`" in text or "\\" in text or "\t" in text:
            return False
        if re.search(r'"[^"\n]*"|(?<!\w)\'[^\'\n]*\'(?!\w)|“[^”]*”|‘[^’]*’', text):
            return False
        if any(re.match(r"^(?: {4,}|\s*(?:[-+*]|\d+[.)])\s+|\s*[>|]|\s*:::)", line)
               for line in text.splitlines()):
            return False
        blocks = parse_blocks(text, "prose")
        if any(block["kind"] not in {"heading", "paragraph"} for block in blocks):
            return False
        structures.append([(block["kind"], _format_normalized(block["text"])) for block in blocks])
    return structures[0] == structures[1]


def _semantic_comparisons(model: dict | None, inventory: dict, store: EvidenceStore,
                          items: dict[tuple[str, str], dict], event_records: list[dict] | None = None) -> dict:
    records = model.get("comparisons", []) if model else []
    if not isinstance(records, list):
        raise EvidenceError("Interpretation comparisons must be an array")
    events = {event["event_id"]: event for event in (store.events() if event_records is None else event_records)}
    documents = {document["id"]: document for document in inventory["documents"]}
    results = {}
    for record in records:
        if not isinstance(record, dict):
            raise EvidenceError("A semantic comparison must be an object")
        key = (record.get("document"), record.get("requirement_id"))
        if key not in items or key in results:
            raise EvidenceError("Comparison references an unknown or duplicated current item")
        if record.get("classification") not in {"equivalent", "behavioral", "removal", "unclear"}:
            raise EvidenceError("Comparison classification must be equivalent, behavioral, removal, or unclear")
        if not isinstance(record.get("reason"), str) or not record["reason"].strip():
            raise EvidenceError("Semantic correspondence needs a source-backed explanation")
        sources = record.get("sources")
        if not isinstance(sources, list) or not sources or set(sources) != set(items[key]["sources"]):
            raise EvidenceError("Semantic comparison must account for all current item's source references")
        event = events.get(record.get("evidence_id"))
        if event is None:
            raise EvidenceError("Semantic comparison references an unknown implementation report")
        prior_id = record.get("evidence_requirement_id", key[1])
        prior_document = record.get("evidence_document", key[0])
        matches = [coverage for coverage in event.get("coverage", [])
                   if coverage["requirement_id"] == prior_id and coverage["document"] == prior_document]
        if len(matches) != 1 or not matches[0].get("version_bound"):
            raise EvidenceError("Semantic comparison needs one retained, version-bound prior requirement")
        if record.get("prior_text") != matches[0].get("text"):
            raise EvidenceError("Semantic comparison must preserve the exact prior requirement text")
        document = documents[key[0]]
        if record.get("requested_hash", document["hash"]) != document["hash"]:
            raise EvidenceError("Semantic comparison belongs to a different requested specification version")
        results[key] = dict(record, evidence_requirement_id=prior_id, evidence_document=prior_document)
    return results


def _latest_applicable(history: list[dict]) -> dict | None:
    # A new checkbox or an incomplete late report cannot erase older valid
    # coverage. Code-stale evidence remains an identifiable historical baseline.
    for evidence in reversed(history):
        coverage = evidence["coverage"]
        if coverage.get("version_bound") and coverage["status"] in {"implemented", "partial"}:
            return evidence
    return history[-1] if history else None


def _uncertain_order(history: list[dict]) -> bool:
    candidates = [record for record in history if record["coverage"].get("version_bound")
                  and record["coverage"]["status"] in {"implemented", "partial"}]
    versions = {(record["coverage"].get("text"), record["coverage"]["status"])
                for record in candidates}
    return len(versions) > 1 and len({record["event"].get("round_id") for record in candidates}) > 1 \
        and any(record.get("chronology") != "workflow time" for record in candidates)


def evidence_summary(record: dict | None) -> dict | None:
    """Expose provenance without repeating entire retained documents in diagrams."""
    if record is None:
        return None
    event, coverage = record["event"], record["coverage"]
    return {"event_id": event["event_id"], "round_id": event.get("round_id"),
            "framework": event["framework"], "origin": event["origin"], "recorded_at": event["recorded_at"],
            "occurred_at": event.get("occurred_at"), "chronology": record.get("chronology"),
            "coverage": {key: coverage[key] for key in ("requirement_id", "status", "version_bound", "details", "limitation")
                         if key in coverage},
            "specification": {"path": coverage["document"], "hash": coverage.get("spec_hash")},
            "implementation": event.get("implementation", {}), "fingerprints": record["fingerprints"]}


def _archived_evidence(path: str, record: dict, inventory: dict) -> bool:
    """Classify history, not completion. Verify moved content only when needed."""
    history = inventory.get("history", [])
    if any(source["path"] == path for source in history):
        return True
    raw = Path(path.removeprefix("external::"))
    absolute = raw if raw.is_absolute() else Path(inventory["project"]["root"]) / raw
    if any(absolute.is_relative_to(root) for root in inventory.get("historical_roots", [])):
        return True
    candidates = [source for source in history if source.get("active_path") == path]
    # A dated directory and matching basename alone do not prove a move.
    if len(candidates) != 1 or not record["coverage"].get("version_bound"):
        return False
    try:
        return digest(read_stable(Path(candidates[0]["absolute_path"]))) == record["coverage"].get("spec_hash")
    except (OSError, ValueError):
        return False


def compare(inventory: dict, store: EvidenceStore, model: dict | None = None,
            use_inspections: bool = False) -> dict:
    """Return item rows; displays never create events or change the baseline.

    Agent-supplied semantic correspondences are structurally source-validated.
    Without them, ambiguous prose edits remain unresolved, rather than guessing
    behavioral equivalence from keyword patterns.
    """
    if model is not None:
        validate_model(model, inventory)
    if Path(inventory["project"]["root"]).resolve() != store.project:
        raise EvidenceError("Comparison inventory and evidence checkout do not match")
    selected = set(inventory.get("scope", [document["id"] for document in inventory["documents"]]))
    interpreted = {document["id"]: document for document in model.get("documents", [])} if model else {}
    documents = {document["id"]: document for document in inventory["documents"]}
    items = {}
    for identity in (document["id"] for document in inventory["documents"] if document["id"] in selected):
        document = documents[identity]
        for item in comparison_items(document, interpreted.get(identity)):
            items[(identity, item["id"])] = item
    event_records = store.events()
    excluded_sources = specification_paths(inventory)
    evidence_index = store.coverage_index(event_records, specification_paths=excluded_sources)
    correspondences = _semantic_comparisons(model, inventory, store, items, event_records)
    inspections = store.inspections(specification_paths=excluded_sources) if use_inspections else []
    rows, warnings, covered_keys = [], [], set()
    if use_inspections and any(identity.startswith("external::") for identity in selected):
        warnings.append("Persisted code inspection of external specification sources is unsupported; external workflow report comparisons remain available")
    for key, item in items.items():
        identity, requirement_id = key
        document = documents[identity]
        requested = requested_text(item, document)
        correspondence = correspondences.get(key)
        prior_id = correspondence["evidence_requirement_id"] if correspondence else requirement_id
        prior_doc = correspondence["evidence_document"] if correspondence else document["path"]
        history = evidence_index.get((prior_doc, prior_id), [])
        evidence = _latest_applicable(history)
        uncertain_order = _uncertain_order(history)
        if correspondence:
            matched = [record for record in history if record["event"]["event_id"] == correspondence["evidence_id"]]
            if not matched or evidence is None or evidence["event"]["event_id"] != correspondence["evidence_id"]:
                if uncertain_order and matched and matched[0]["coverage"].get("version_bound") and matched[0]["coverage"]["status"] in {"implemented", "partial"}:
                    evidence = matched[0]
                else:
                    raise EvidenceError("Semantic correspondence is not based on the latest applicable requirement evidence")
        covered_keys.add((prior_doc, prior_id))
        row = {"document": document["path"], "requirement_id": requirement_id,
               "label": item["label"], "requested": requested, "implemented": None,
               "status": "unknown", "difference": "unresolved", "evidence": evidence_summary(evidence),
               "verification": evidence.get("verification") if evidence else None,
               "inspection": None, "reason": "Implementation reference missing; --check-code is available",
               "sources": list(item["sources"]), "difference_basis": "workflow reports"}
        if evidence:
            if len(history) > 1 and evidence.get("chronology") != "workflow time":
                warnings.append(f"{document['path']}: reports are ordered by delivery; actual workflow times were not supplied for all records")
            coverage = evidence["coverage"]
            row["implemented"] = coverage.get("text")
            if coverage["status"] == "task-progress":
                row["status"] = "task progress"
                row["reason"] = "Task progress was reported; requirement implementation remains unknown"
            elif not coverage.get("version_bound"):
                row["reason"] = "Report lacks binding to the actually implemented specification version"
            else:
                row["status"] = "reported implemented" if coverage["status"] == "implemented" else "partial"
                implemented = coverage["text"]
                if requested == implemented:
                    row["difference"] = "unchanged"
                    row["reason"] = "Requested source matches the reported implemented requirement"
                elif _prose_whitespace_equivalent(requested, implemented):
                    row["difference"] = "documentation-only"
                    row["reason"] = "Only plain-prose spacing or line wrapping changed; block structure is unchanged"
                elif correspondence:
                    row["difference"] = {"equivalent": "documentation-only", "behavioral": "behavioral",
                                         "removal": "removal-requested", "unclear": "unresolved"}[correspondence["classification"]]
                    row["reason"] = correspondence["reason"]
                else:
                    row["difference"] = "unresolved"
                    row["reason"] = "Requested source changed; behavioral equivalence needs source-backed interpretation"
                if coverage["status"] == "partial":
                    row["reason"] += "; only part of the requirement has reported implementation coverage"
                    if coverage.get("details"):
                        row["reason"] += "; coverage details: " + str(coverage["details"])
                if evidence["fingerprints"]["status"] != "current":
                    row["status"] = "stale" if evidence["fingerprints"]["status"] == "stale" else "unknown"
                    row["reason"] += "; " + evidence["fingerprints"]["reason"]
            if history and history[-1] is not evidence and (not history[-1]["coverage"].get("version_bound") or history[-1]["coverage"]["status"] == "task-progress"):
                warnings.append(f"{document['path']}: later-delivered limited progress did not replace the selected version-bound implementation reference")
        row["temporal_order_uncertain"] = uncertain_order
        if uncertain_order:
            row["candidate_report_difference"] = row["difference"]
            row["report_alternatives"] = [dict(evidence_summary(record), implemented=record["coverage"].get("text")) for record in history
                                          if record is not evidence and record["coverage"].get("version_bound")]
            row["status"] = "unknown"
            row["difference"] = "unresolved"
            row["reason"] += "; competing report versions have uncertain workflow order; this is a candidate reference, not a confirmed latest implementation"
        row["report_difference"] = row["difference"]
        row["report_status"] = row["status"]
        row["report_reason"] = row["reason"]
        if use_inspections:
            matches = [(finding, result) for finding in inspections for result in finding["findings"]
                       if result["document"] == document["path"] and result["requirement_id"] == requirement_id]
            if matches:
                finding, result = matches[-1]
                row["inspection"] = {"record": finding, "finding": result}
                if finding["applicable"]:
                    row["difference_basis"] = "current code inspection"
                    row["status"] = {"supported": "code supported", "partial": "code partial",
                                     "contradicted": "contradicted", "not-found": "not found", "unclear": "unclear"}[result["status"]]
                    row["reason"] = result["reason"]
                    if result["status"] == "supported":
                        row["difference"] = "unchanged"
                        row["reason"] += "; current requested behavior has code support within the inspected scope"
                    elif result["status"] == "contradicted":
                        row["difference"] = "behavioral"
                        if evidence and evidence["coverage"]["status"] == "implemented" and row["report_difference"] in {"unchanged", "documentation-only"}:
                            row["reason"] += "; current code contradicts retained workflow completion evidence"
                        elif evidence:
                            row["reason"] += "; earlier workflow evidence is retained separately from this current requirement finding"
                    if not finding["complete"]:
                        warnings.append("Inspection incomplete; remaining declared scope requires explicit continuation")
                else:
                    warnings.append(f"{document['path']}: saved inspection is stale and cannot establish current code support")
                    row["reason"] += "; prior code inspection is stale"
            else:
                warnings.append(f"{document['path']}: no saved inspection for {item['label']}; agent inspection is required")
        rows.append(row)
    # Missing files are unresolved provenance changes, not automatic requests to
    # delete behavior. Restrict local views to evidence within their known scope.
    if selected == set(documents):
        historical = {key: _latest_applicable(records) for key, records in evidence_index.items()}
        paths = {document["path"] for document in documents.values()}
        for (path, requirement_id), historical_evidence in historical.items():
            if (path, requirement_id) in covered_keys:
                continue
            coverage = historical_evidence["coverage"]
            available = path in paths
            if not available and _archived_evidence(path, historical_evidence, inventory):
                continue
            rows.append({"document": path, "requirement_id": requirement_id,
                         "label": "Previously evidenced requirement not located" if available else "Previously evidenced source unavailable",
                         "requested": "Requirement correspondence unresolved" if available else "Source unavailable",
                         "implemented": coverage.get("text"), "status": "unknown", "difference": "unresolved" if available else "source-unavailable",
                         "evidence": evidence_summary(historical_evidence), "verification": historical_evidence.get("verification"),
                         "inspection": None, "sources": [],
                         "reason": "A missing or renamed section needs explicit correspondence; it does not establish a behavior-removal request"
                         if available else "A missing or moved document does not establish a behavior-removal request"})
    if not rows:
        warnings.append("No substantive selected source content was available for comparison")
    return {"rows": rows, "warnings": list(dict.fromkeys(warnings)),
            "basis": "Workflow completion/progress reports; verification is separate"
            + ("; requested direct code inspection findings are shown separately" if use_inspections else ""),
            "project": inventory["project"], "snapshot": inventory.get("snapshot")}
