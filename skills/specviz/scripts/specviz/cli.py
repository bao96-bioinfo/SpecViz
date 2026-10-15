"""Shared commands for the skill; advanced flags exchange agent records."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import uuid
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .comparison import compare
from .core import ValidationError, validate_inventory, validate_model
from .discovery import discover, resolve_project, select_inventory, specification_paths
from .evidence import EvidenceStore, PersistenceError, default_state_directory, implementation_identity
from .inspection import validate_inspection
from .views import changes_view, overview_view, show_view
from .pagination import paginate
from .session import ViewStore


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Specification diagrams directly as text: overview, show, changes.")
    result.add_argument("action", nargs="?", default="overview", choices=("overview", "show", "changes"))
    result.add_argument("paths", nargs="*", help="Folder for overview; files for show; folders/files for changes")
    result.add_argument("--detailed", action="store_true", help="Expand annotations in the same diagram")
    result.add_argument("--check-code", action="store_true", help="Changes only: request source-backed agent code inspection")
    result.add_argument("--project", type=Path, help="Explicit project root")
    result.add_argument("--version", action="version", version=f"SpecViz {__version__}")
    internal = result.add_argument_group("Agent exchange and local helper options")
    internal.add_argument("--json", action="store_true", help="Return source inventory and evidence for agent interpretation")
    internal.add_argument("--omit-overview-hint", action="store_true", help="Fresh overviews only: let the skill supply a contextual next step")
    internal.add_argument("--model", type=Path, help="Validated interpretation JSON, stored outside the project")
    internal.add_argument("--inspection", type=Path, help="Observational inspection JSON; requires changes --check-code")
    internal.add_argument("--event", type=Path, help="Import one workflow handoff JSON without creating display evidence")
    internal.add_argument("--reports", type=Path, nargs="*", default=[], help="Additional persisted handoff reports")
    internal.add_argument("--state-dir", type=Path, help="State outside the checkout (or SPECVIZ_STATE_DIR)")
    internal.add_argument("--session", help="Distinct identity for this conversation's file selections")
    internal.add_argument("--continue-view", help="Continue one immutable previously displayed view")
    internal.add_argument("--page", type=int, default=1, help="One-based continuation page")
    internal.add_argument("--max-lines", type=int, default=100, help="Bound each output part")
    internal.add_argument("--width", type=int, default=80, help="Diagram body width")
    internal.add_argument("--capture-round", help="Capture sources when an implementation round actually begins")
    internal.add_argument("--framework", choices=("openspec", "spec-kit", "bmad", "superpowers", "kiro"))
    internal.add_argument("--host", default="agent", help="Originating host in an explicit workflow handoff")
    internal.add_argument("--generation-ready", help="Opt-in handoff: generated specification group is ready")
    return result


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValidationError("Agent record must be a JSON object")
    return value


def _generation_enabled() -> bool:
    manifest = Path(__file__).resolve().parents[2] / ".specviz-install.json"
    try:
        return _load(manifest).get("generation_handoff") is True
    except (OSError, ValueError):
        return False


def _report_paths(inventory: dict, explicit: list[Path]) -> list[Path]:
    # Supported persisted handoffs are identified by their format, never by a
    # completed task checkbox. Do not scan dependency trees or unrelated roots.
    candidates = set(path.resolve() for path in explicit)
    for document in inventory["documents"]:
        if document["id"] not in inventory.get("scope", []):
            continue
        parent = Path(document["absolute_path"]).parent
        candidates.update(path.resolve() for path in parent.glob("*.specviz-report.json"))
    return sorted(candidates)


def _request(inventory: dict, comparison: dict) -> dict:
    return {"observational": True, "tests_executed": False,
            "scope": inventory["scope"], "requirements": comparison["rows"],
            "instructions": "Read relevant code and existing test evidence; follow references. Submit version-bound findings. Do not execute tests or source commands, edit files, or infer absence from a failed keyword search."}


class _UnavailableEvidence:
    def __init__(self, project: Path):
        self.project = project

    def events(self):
        return []

    def coverage_history(self, *args):
        return []

    def coverage_index(self, *args, **kwargs):
        return {}

    def inspections(self, **kwargs):
        return []


def _continuation(token: str, page: int, session: str | None) -> str:
    command = f"\nContinue this view: --continue-view {token} --page {page}"
    if session:
        command += " --session " + shlex.quote(session)
    return command + "\n"


def run(args: argparse.Namespace) -> dict | str:
    if args.omit_overview_hint and args.action != "overview":
        raise ValidationError("--omit-overview-hint is available only for overview")
    if args.check_code and args.action != "changes":
        raise ValidationError("--check-code is available through changes; use changes <scope> --check-code")
    if args.inspection and not args.check_code:
        raise ValidationError("Inspection findings require changes --check-code")
    if args.action == "overview" and len(args.paths) > 1:
        raise ValidationError("overview accepts one folder; use show for multiple files")
    if args.width < 30 or args.max_lines < 12 or args.page < 1:
        raise ValidationError("Use width >= 30, max-lines >= 12, and page >= 1")
    project = resolve_project(args.project)
    state_dir = args.state_dir or default_state_directory()
    try:
        views = ViewStore(project, state_dir)
        view_warning = None
    except (ValueError, OSError) as exc:
        views = None
        view_warning = str(exc)
    if args.continue_view:
        if views is None:
            raise ValidationError("View state unavailable; request a new overview")
        delivery_warning = ""
        try:
            view = views.deliver(args.continue_view, args.page, args.session)
        except OSError:
            view = views.load(args.continue_view)
            expected = view.get("conversation")
            from .core import digest
            if expected is not None and expected != (digest(args.session) if args.session else None):
                raise ValidationError("Continuation belongs to another conversation; use the original --session")
            delivery_warning = "\nSelection storage unavailable; select newly shown files by path.\n"
        if args.page > len(view["pages"]):
            raise ValidationError("No such continuation page")
        output = view["pages"][args.page - 1] + delivery_warning
        if args.page < len(view["pages"]):
            output += _continuation(args.continue_view, args.page + 1, args.session)
        return output
    paths = args.paths
    if any(path.isdecimal() for path in paths):
        if not args.session or views is None:
            raise ValidationError("Numbered selection needs this conversation's --session; otherwise select by file path")
        paths = views.select(paths, args.session)
    inventory = discover(project=project, selections=paths or None)
    if view_warning:
        inventory["warnings"].append(view_warning)
    if args.action == "show" and not paths:
        raise ValidationError("show needs one or more files; request overview to choose them")
    if args.action == "overview" and paths and not (project / paths[0]).is_dir():
        raise ValidationError("Local overview needs a folder; use show <file> for a file")
    if args.action == "show":
        for path in paths:
            if (project / path).is_dir():
                raise ValidationError("show accepts files; use overview <folder> for a folder")
    validate_inventory(inventory)
    model = validate_model(_load(args.model), inventory) if args.model else None
    if args.generation_ready:
        if args.action != "overview" or paths:
            raise ValidationError("Generation handoffs use a whole-project overview")
        if not _generation_enabled():
            return {"generation_handoff": "disabled", "message": "Use an explicit overview, or enable generation handoff during installation"} if args.json else "Generation handoff disabled. Use an explicit overview command."
        inventory["current_work"] = args.generation_ready
    receipts = []
    comparison = None
    if args.event or args.capture_round or args.inspection or args.action == "changes":
        try:
            store = EvidenceStore(project, state_dir)
        except PersistenceError as exc:
            if args.event or args.capture_round or args.inspection:
                raise
            inventory["warnings"].append(str(exc))
            unavailable_model = dict(model, comparisons=[]) if model else None
            comparison = compare(inventory, _UnavailableEvidence(project), unavailable_model, use_inspections=False)
            comparison["basis"] = "Evidence storage unavailable; implementation unknown"
            comparison["warnings"].append(str(exc))
            store = None
        if store:
            if args.capture_round:
                if not args.framework:
                    raise ValidationError("Capturing a workflow round requires --framework")
                event = {"schema_version": SCHEMA_VERSION, "event_id": f"begin:{args.framework}:{args.capture_round}",
                         "event": "begin", "framework": args.framework, "round_id": args.capture_round,
                         "scope": paths or inventory["scope"], "origin": {"kind": "handoff", "source": "Explicit implementation-start handoff", "host": args.host},
                         "specifications": [{"path": d["path"], "hash": d["hash"], "text": d["text"]} for d in inventory["documents"] if d["id"] in inventory["scope"]],
                         "implementation": implementation_identity(project, specification_paths=specification_paths(inventory)), "coverage": []}
                prior = [event for event in store.events() if event.get("round_id") == args.capture_round and event["event"] == "begin"]
                if prior and (prior[0]["framework"] != args.framework or prior[0]["scope"] != event["scope"]):
                    raise ValidationError("A resumed round must retain its framework and declared scope")
                receipts.append({"resumed": True, "event": prior[0]} if prior else store.ingest(event))
            if args.event:
                receipts.append(store.ingest(_load(args.event)))
            if args.action == "changes":
                for path in _report_paths(inventory, args.reports):
                    try:
                        receipts.append(store.ingest(_load(path)))
                    except (ValueError, OSError) as exc:
                        inventory["warnings"].append(f"Report not imported: {path}: {exc}")
                if args.inspection:
                    record = validate_inspection(_load(args.inspection), inventory, model)
                    receipts.append(store.save_inspection(record))
                comparison = compare(inventory, store, model, use_inspections=args.check_code)
    if args.json:
        if comparison is not None or receipts:
            result = {"inventory": inventory, "comparison": comparison, "receipts": receipts}
            if args.check_code:
                result["inspection_request"] = _request(inventory, comparison)
            return result
        return inventory
    if args.action == "changes":
        view = changes_view(inventory, comparison, model, args.detailed, args.width)
    elif args.action == "show":
        view = show_view(inventory, model=model, detailed=args.detailed, width=args.width)
    else:
        view = overview_view(inventory, model, args.detailed, args.width, omit_hint=args.omit_overview_hint)
    if receipts:
        view.text("Workflow evidence handled separately from this display.")
    rendered_pages = paginate(view, args.max_lines)
    pages = [page.text for page in rendered_pages]
    if args.page > len(pages):
        raise ValidationError("No such output page")
    if views is None:
        return view.render() + "\nView persistence unavailable; showing the complete view. Select files by path.\n"
    try:
        token = views.save(inventory, pages, args.session, [page.documents for page in rendered_pages], args.page)
    except OSError as exc:
        return view.render() + f"\nView persistence unavailable: {exc}\nShowing the complete view. Select files by path.\n"
    output = pages[args.page - 1]
    if args.page < len(pages):
        output += _continuation(token, args.page + 1, args.session)
    return output


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_intermixed_args(argv)
    try:
        result = run(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"SpecViz: {exc}", file=sys.stderr)
        return 2
    if isinstance(result, dict):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result, end="" if result.endswith("\n") else "\n")
    return 0
