"""Version-bound workflow evidence, persisted outside the source checkout.

Reports are claims with provenance, not a proof of correctness. This module never
executes source content, workflows, or tests, and never reads current documents to
invent the specification version associated with an older report.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = 1
FRAMEWORKS = {"openspec", "spec-kit", "bmad", "superpowers", "kiro"}
FRAMEWORK_ALIASES = {"GitHub Spec Kit": "spec-kit", "BMAD Method": "bmad",
                     "OpenSpec": "openspec", "Superpowers": "superpowers",
                     "Kiro Specs": "kiro", "speckit": "spec-kit"}
EVENTS = {"begin", "progress", "complete", "verify", "specifications-ready"}
EXCLUDED_DIRECTORIES = {".git", ".agents", ".claude", ".agent", ".kiro", ".specify",
                        "openspec", "node_modules", "vendor", ".venv", "venv",
                        "__pycache__", "dist", "build", ".pytest_cache", ".specviz"}


class EvidenceError(ValueError):
    """A report or stored record cannot be trusted under this schema."""


class PersistenceError(EvidenceError):
    """Durable storage was unavailable; no completion should be inferred."""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def project_identity(project: Path) -> str:
    """Canonical roots isolate copied checkouts and independently edited worktrees."""
    root = project.resolve()
    identity = str(root)
    git = root / ".git"
    if git.is_file():
        identity += "\n" + git.read_text(encoding="utf-8").strip()
    return digest(identity)


def _relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise EvidenceError("Evidence paths must be non-empty relative paths")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value:
        raise EvidenceError(f"Unsafe evidence path: {value!r}")
    return path.as_posix()


def _hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _implementation(value: Any) -> dict:
    if not isinstance(value, dict):
        raise EvidenceError("implementation must be an object")
    files = value.get("files", {})
    if not isinstance(files, dict):
        raise EvidenceError("implementation.files must map paths to SHA-256 fingerprints")
    for path, fingerprint in files.items():
        _relative_path(path)
        if path.startswith("external::"):
            raise EvidenceError("External implementation fingerprints are unsupported; declare local relevant source files")
        if not _hash(fingerprint):
            raise EvidenceError(f"Invalid implementation fingerprint for {path}")
    if not isinstance(value.get("complete_manifest", False), bool):
        raise EvidenceError("implementation.complete_manifest must be a boolean")
    if value.get("complete_manifest") and not value.get("manifest_available", True):
        raise EvidenceError("An unavailable manifest cannot be complete")
    excluded = value.get("excluded_specifications", [])
    if not isinstance(excluded, list):
        raise EvidenceError("excluded_specifications must be an array of specification identities")
    for path in excluded:
        _relative_path(path)
    return value


def validate_event(payload: dict) -> dict:
    """Validate a portable explicit handoff without assuming missing provenance."""
    if not isinstance(payload, dict):
        raise EvidenceError("An evidence event must be a JSON object")
    event = copy.deepcopy(payload)
    if event.get("schema_version") != SCHEMA_VERSION:
        raise EvidenceError("Unsupported evidence schema_version; expected 1")
    if event.get("event") not in EVENTS:
        raise EvidenceError("Unknown evidence event")
    if not isinstance(event.get("event_id"), str) or not event["event_id"].strip():
        raise EvidenceError("An event_id is required for idempotent delivery")
    framework = FRAMEWORK_ALIASES.get(event.get("framework"), event.get("framework"))
    if framework not in FRAMEWORKS:
        raise EvidenceError("Unsupported evidence framework")
    event["framework"] = framework
    if event["event"] != "specifications-ready" and not isinstance(event.get("round_id"), str):
        raise EvidenceError("A workflow round_id is required")
    if event.get("round_id") == "":
        raise EvidenceError("round_id cannot be empty")
    scope = event.get("scope")
    if not isinstance(scope, list) or not scope or not all(isinstance(s, str) and s for s in scope):
        raise EvidenceError("scope must name the declared feature/change or selected files")
    origin = event.get("origin")
    if not isinstance(origin, dict) or origin.get("kind") not in {"handoff", "native-report"}:
        raise EvidenceError("origin.kind must identify handoff or native-report")
    if not isinstance(origin.get("source"), str) or not origin["source"]:
        raise EvidenceError("origin.source must identify the actual report")
    if origin["kind"] == "native-report" and not origin.get("format"):
        raise EvidenceError("A native report must identify its supported format")
    if "occurred_at" in event:
        try:
            occurred = datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00"))
            if occurred.tzinfo is None:
                raise ValueError("Timezone is required")
        except (AttributeError, TypeError, ValueError) as exc:
            raise EvidenceError("occurred_at must be an ISO timestamp with a timezone") from exc
    specifications = event.setdefault("specifications", [])
    if not isinstance(specifications, list):
        raise EvidenceError("specifications must be an array of retained source versions")
    seen = set()
    for source in specifications:
        if not isinstance(source, dict):
            raise EvidenceError("A specification version must be an object")
        _relative_path(source.get("path"))
        if not isinstance(source.get("text"), str) or not _hash(source.get("hash")):
            raise EvidenceError("A retained specification requires exact text and SHA-256 hash")
        if digest(source["text"]) != source["hash"]:
            raise EvidenceError(f"Specification hash does not match retained text: {source['path']}")
        key = (source["path"], source["hash"])
        if key in seen:
            raise EvidenceError("Duplicate retained specification version")
        seen.add(key)
    event["implementation"] = _implementation(event.get("implementation", {}))
    coverage = event.setdefault("coverage", [])
    if not isinstance(coverage, list):
        raise EvidenceError("coverage must be an array")
    for item in coverage:
        if not isinstance(item, dict) or not isinstance(item.get("requirement_id"), str) or not item["requirement_id"]:
            raise EvidenceError("Coverage requires a requirement_id")
        _relative_path(item.get("document"))
        if item.get("status") not in {"implemented", "partial", "task-progress"}:
            raise EvidenceError("Invalid requirement coverage status")
        if item.get("spec_hash") is not None and not _hash(item["spec_hash"]):
            raise EvidenceError("Invalid covered specification hash")
        if item.get("text") is not None and not isinstance(item["text"], str):
            raise EvidenceError("Covered requirement text must be a string")
        if "sources" in item and (not isinstance(item["sources"], list) or not item["sources"]
                                  or not all(isinstance(reference, str) for reference in item["sources"])):
            raise EvidenceError("Coverage sources must be a non-empty array of source-block identities")
    verification = event.get("verification")
    if verification is not None:
        if not isinstance(verification, dict) or not isinstance(verification.get("executed"), bool):
            raise EvidenceError("verification must explicitly say whether checks executed")
        checks = verification.get("checks", [])
        if not isinstance(checks, list) or not all(isinstance(c, dict) and isinstance(c.get("command"), str)
                                                and isinstance(c.get("result"), str) for c in checks):
            raise EvidenceError("verification checks require command and result text")
        if verification["executed"] and not checks:
            raise EvidenceError("Executed verification must identify its checks")
    if event["event"] == "verify" and verification is None:
        raise EvidenceError("A verification event requires verification evidence")
    if event["event"] == "complete" and event.get("declared_complete") is not True:
        raise EvidenceError("Only declared scope completion can close a round")
    if event["framework"] == "bmad" and event.get("workflow_status") == "built" and event["event"] == "complete":
        raise EvidenceError("BMAD built work is progress; an explicit done/completion report is required")
    return event


def normalize_handoff(framework: str, payload: dict) -> dict:
    """The tested mapping for all five frameworks is an explicit source-bound handoff.

    Native task lists are deliberately not advertised as completion reports.
    """
    event = dict(payload, framework=framework)
    if event.get("origin", {}).get("kind") != "handoff":
        raise EvidenceError("This adapter supports explicit handoffs; native report ingestion is unavailable")
    return validate_event(event)


def _source_paths(project: Path, unavailable: list | None = None,
                  specification_paths: set[str] | None = None) -> list[Path]:
    sources = []
    unavailable = unavailable if unavailable is not None else []
    specification_paths = specification_paths or set()
    def failure(error):
        path = Path(error.filename or project)
        unavailable.append({"path": os.path.relpath(path, project), "reason": str(error)})
    for directory, child_dirs, files in os.walk(project, followlinks=False, onerror=failure):
        child_dirs[:] = sorted(name for name in child_dirs if name not in EXCLUDED_DIRECTORIES
                               and not name.startswith(".specviz"))
        for name in child_dirs[:]:
            path = Path(directory) / name
            if path.is_symlink():
                child_dirs.remove(name)
                unavailable.append({"path": path.relative_to(project).as_posix(),
                                    "reason": "Symbolic-link directory not traversed; declare relevant source paths explicitly"})
        for name in sorted(files):
            path = Path(directory) / name
            if path.relative_to(project).as_posix() in specification_paths:
                continue
            if name.endswith(".specviz-report.json") or name.startswith(".specviz-"):
                continue
            if path.suffix.lower() in {".md", ".rst", ".txt", ".sqlite3", ".db", ".pyc"} or name == "LICENSE":
                continue
            if path.is_symlink():
                unavailable.append({"path": path.relative_to(project).as_posix(),
                                    "reason": "Symbolic-link source requires explicit relevant-path declaration"})
                continue
            sources.append(path)
    return sources


def implementation_identity(project: Path, paths: list[str] | None = None,
                            specification_paths: list[str] | None = None) -> dict:
    """Read fingerprints, including dirty files; absence of a path is not concealed."""
    root = project.resolve()
    excluded = {_relative_path(path) for path in specification_paths or []}
    files, unavailable = {}, []
    candidates = _source_paths(root, unavailable, excluded) if paths is None else [root / _relative_path(p) for p in paths
                                                                                if _relative_path(p) not in excluded]
    for path in candidates:
        relative = path.relative_to(root).as_posix()
        try:
            if not path.resolve().is_relative_to(root):
                raise OSError("Source escapes project boundary")
            before = path.stat()
            content = path.read_bytes()
            after = path.stat()
            if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                raise OSError("Source changed during inspection")
            files[relative] = hashlib.sha256(content).hexdigest()
        except OSError as exc:
            unavailable.append({"path": relative, "reason": str(exc)})
    return {"files": files, "revision": None, "complete_manifest": paths is None and not unavailable,
            "manifest_available": not unavailable, "unavailable": unavailable,
            "excluded_specifications": sorted(excluded),
            "limitation": "Conservative source manifest; unrelated source changes can invalidate evidence"
            if paths is None else "Only the declared relevant source files were fingerprinted"}


def fingerprint_status(project: Path, implementation: dict,
                       specification_paths: list[str] | None = None) -> dict:
    """Check old evidence against current relevant code, never against newer specs."""
    if not implementation or not implementation.get("files") and not implementation.get("complete_manifest"):
        return {"status": "unknown", "changed": [], "reason": "Implementation fingerprints unavailable"}
    excluded = set(implementation.get("excluded_specifications", [])) | set(specification_paths or [])
    expected = {path: value for path, value in implementation.get("files", {}).items() if path not in excluded}
    if not expected and not implementation.get("complete_manifest"):
        return {"status": "unknown", "changed": [], "reason": "No implementation fingerprints remain after excluding specification sources"}
    current = implementation_identity(project, None if implementation.get("complete_manifest") else list(expected),
                                      specification_paths=list(excluded))
    changed = sorted(path for path in set(expected) | set(current["files"])
                     if expected.get(path) != current["files"].get(path))
    if current["unavailable"]:
        return {"status": "stale", "changed": changed, "reason": "Referenced implementation files unavailable",
                "unavailable": current["unavailable"]}
    return {"status": "stale" if changed else "current", "changed": changed,
            "reason": "Relevant implementation changed" if changed else "Recorded source fingerprints still match"}


def default_state_directory() -> Path:
    if os.environ.get("SPECVIZ_STATE_DIR"):
        return Path(os.environ["SPECVIZ_STATE_DIR"]).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SpecViz"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "SpecViz"
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))) / "specviz"


class EvidenceStore:
    """Append-only event history and separate inspection records, one DB per checkout."""

    def __init__(self, project: Path, state_dir: Path | None = None):
        self.project = Path(project).resolve()
        self.project_id = project_identity(self.project)
        self.state_dir = Path(state_dir or default_state_directory()).resolve()
        if self.state_dir.is_relative_to(self.project):
            raise PersistenceError("SpecViz state must be outside the project; set SPECVIZ_STATE_DIR")
        self.path = self.state_dir / f"{self.project_id}.sqlite3"
        try:
            self.state_dir.mkdir(parents=True, exist_ok=True)
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if version not in {0, SCHEMA_VERSION}:
                    raise PersistenceError(f"Unsupported stored schema version {version}; history retained")
                if version == 0:
                    existing = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    if existing:
                        raise PersistenceError("Unrecognized database; refusing to replace existing state")
                    db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                    db.execute("CREATE TABLE events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)")
                    db.execute("CREATE TABLE inspections (sequence INTEGER PRIMARY KEY AUTOINCREMENT, inspection_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)")
                    db.execute("INSERT INTO metadata VALUES ('project', ?)", (str(self.project),))
                    db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                root = db.execute("SELECT value FROM metadata WHERE key='project'").fetchone()
                if root is None or root[0] != str(self.project):
                    raise PersistenceError("Stored project provenance does not match this checkout")
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError(f"Cannot open SpecViz evidence state: {exc}") from exc

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA busy_timeout=5000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def events(self) -> list[dict]:
        try:
            with self._connection() as db:
                return [json.loads(row[0]) for row in db.execute("SELECT payload FROM events ORDER BY sequence")]
        except (sqlite3.Error, json.JSONDecodeError) as exc:
            raise PersistenceError(f"Cannot read SpecViz evidence: {exc}") from exc

    def ingest(self, payload: dict) -> dict:
        event = validate_event(payload)
        if event["origin"]["kind"] == "native-report":
            raise EvidenceError("No native persisted report format is advertised yet; use an explicit handoff")
        provenance = event.get("project")
        if provenance is not None:
            if not isinstance(provenance, dict) or provenance.get("id", self.project_id) != self.project_id:
                raise EvidenceError("Report project identity does not match this checkout")
            if provenance.get("root") and Path(provenance["root"]).resolve() != self.project:
                raise EvidenceError("Report project root does not match this checkout")
        serialized_source = json.dumps(event, sort_keys=True, separators=(",", ":"))
        try:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                old = db.execute("SELECT payload FROM events WHERE event_id=?", (event["event_id"],)).fetchone()
                if old:
                    existing = json.loads(old[0])
                    if existing.get("delivery_hash") != digest(serialized_source):
                        raise EvidenceError("An event_id was reused with a conflicting payload")
                    return {"recorded": False, "duplicate": True, "event": existing}
                prior = [json.loads(r[0]) for r in db.execute("SELECT payload FROM events ORDER BY sequence")]
                round_events = [e for e in prior if e.get("round_id") == event.get("round_id")
                                and event.get("round_id") is not None]
                if any(e["framework"] != event["framework"] or e["scope"] != event["scope"] for e in round_events):
                    raise EvidenceError("A resumed round must retain its framework and declared scope")
                if any(e["event"] == "complete" for e in round_events) and event["event"] in {"begin", "progress", "complete"}:
                    raise EvidenceError("A completed round cannot be reopened; begin a new round")
                sources = {(s["path"], s["hash"]): s for e in round_events + [event] for s in e["specifications"]}
                event["warnings"] = []
                for coverage in event["coverage"]:
                    source = sources.get((coverage["document"], coverage.get("spec_hash")))
                    bound_text = coverage.get("text")
                    source_backed = False
                    if source and bound_text:
                        source_backed = bound_text in source["text"]
                        if coverage.get("sources"):
                            from .core import parse_blocks
                            from .comparison import requested_text
                            blocks = parse_blocks(source["text"], source["path"])
                            known = {block["id"] for block in blocks}
                            if not set(coverage["sources"]) <= known:
                                raise EvidenceError("Coverage references an invented retained source block")
                            source_backed = bound_text == requested_text(coverage, dict(source, blocks=blocks))
                    coverage["version_bound"] = bool(source and bound_text and source_backed)
                    if coverage["version_bound"]:
                        coverage["specification"] = source
                    else:
                        coverage["limitation"] = "Requirement text is not bound to a retained implemented specification version"
                        event["warnings"].append(coverage["limitation"])
                    if coverage["status"] == "task-progress":
                        coverage["limitation"] = "Task progress does not establish requirement compliance"
                event["project"] = {"id": self.project_id, "root": str(self.project)}
                event["recorded_at"] = datetime.now(timezone.utc).isoformat()
                event["delivery_hash"] = digest(serialized_source)
                db.execute("INSERT INTO events(event_id,payload) VALUES (?,?)",
                           (event["event_id"], json.dumps(event, sort_keys=True)))
                return {"recorded": True, "duplicate": False, "event": event}
        except sqlite3.Error as exc:
            raise PersistenceError(f"Cannot record complete SpecViz event: {exc}") from exc

    def latest(self, requirement_id: str, document: str | None = None) -> dict | None:
        matches = self.coverage_history(requirement_id, document)
        return matches[-1] if matches else None

    def coverage_history(self, requirement_id: str, document: str | None = None) -> list[dict]:
        index = self.coverage_index()
        if document is not None:
            return index.get((document, requirement_id), [])
        matches = [record for (_, identity), records in index.items() if identity == requirement_id for record in records]
        matches.sort(key=lambda record: record["delivery_sequence"])
        return self._chronological(matches)

    @staticmethod
    def _chronological(matches: list[dict]) -> list[dict]:
        timed = bool(matches) and all(record["event"].get("occurred_at") for record in matches)
        if timed:
            matches.sort(key=lambda record: datetime.fromisoformat(record["event"]["occurred_at"].replace("Z", "+00:00")))
        for record in matches:
            record["chronology"] = "workflow time" if timed else "delivery order; workflow time unavailable"
        return matches

    def coverage_index(self, events: list[dict] | None = None,
                       specification_paths: list[str] | None = None) -> dict:
        """Index one evidence snapshot; fingerprint identical code manifests once."""
        events = self.events() if events is None else events
        index, fingerprints = {}, {}
        for sequence, event in enumerate(events):
            if event["event"] not in {"progress", "complete"}:
                continue
            implementation = event.get("implementation", {})
            exclusions = set(specification_paths or []) | {source["path"] for source in event.get("specifications", [])}
            exclusions.update(coverage["specification"]["path"] for coverage in event.get("coverage", [])
                              if coverage.get("specification"))
            identity = json.dumps([implementation, sorted(exclusions)], sort_keys=True)
            if identity not in fingerprints:
                fingerprints[identity] = fingerprint_status(self.project, implementation, list(exclusions))
            verification_events = [e for e in events if e["event"] == "verify"
                                   and e.get("round_id") == event.get("round_id")
                                   and e.get("implementation", {}).get("files") == implementation.get("files")]
            verification = verification_events[-1].get("verification") if verification_events else event.get("verification")
            for coverage in event["coverage"]:
                index.setdefault((coverage["document"], coverage["requirement_id"]), []).append(
                    {"coverage": coverage, "event": event, "verification": verification,
                     "delivery_sequence": sequence, "fingerprints": fingerprints[identity]})
        return {key: self._chronological(records) for key, records in index.items()}

    def save_inspection(self, payload: dict) -> dict:
        finding = validate_inspection(payload)
        for source in finding["specifications"]:
            if source["path"].startswith("external::"):
                raise EvidenceError("Persisted inspection of external specification sources is unsupported; use report comparison or select local files")
            path = self.project / source["path"]
            try:
                if not path.resolve().is_relative_to(self.project) or hashlib.sha256(path.read_bytes()).hexdigest() != source["hash"]:
                    raise EvidenceError("Inspection specification snapshot no longer matches its source")
            except OSError as exc:
                raise EvidenceError("Inspection specification source unavailable") from exc
        if fingerprint_status(self.project, finding["implementation"], [source["path"] for source in finding["specifications"]])["status"] != "current":
            raise EvidenceError("Inspection implementation fingerprints are missing or stale")
        finding["project"] = {"id": self.project_id, "root": str(self.project)}
        serialized = json.dumps(finding, sort_keys=True)
        try:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                old = db.execute("SELECT payload FROM inspections WHERE inspection_id=?", (finding["inspection_id"],)).fetchone()
                if old:
                    if old[0] != serialized:
                        raise EvidenceError("An inspection_id was reused with conflicting findings")
                    return {"recorded": False, "duplicate": True}
                db.execute("INSERT INTO inspections(inspection_id,payload) VALUES (?,?)", (finding["inspection_id"], serialized))
                return {"recorded": True, "duplicate": False}
        except sqlite3.Error as exc:
            raise PersistenceError(f"Cannot record SpecViz inspection: {exc}") from exc

    def inspections(self, specification_paths: list[str] | None = None) -> list[dict]:
        try:
            with self._connection() as db:
                findings = [json.loads(row[0]) for row in db.execute("SELECT payload FROM inspections ORDER BY sequence")]
        except (sqlite3.Error, json.JSONDecodeError) as exc:
            raise PersistenceError(f"Cannot read SpecViz inspections: {exc}") from exc
        for finding in findings:
            exclusions = set(specification_paths or []) | {source["path"] for source in finding["specifications"]}
            finding["fingerprints"] = fingerprint_status(self.project, finding["implementation"], list(exclusions))
            changed = []
            for source in finding["specifications"]:
                try:
                    path = self.project / source["path"]
                    if not path.resolve().is_relative_to(self.project) or hashlib.sha256(path.read_bytes()).hexdigest() != source["hash"]:
                        changed.append(source["path"])
                except OSError:
                    changed.append(source["path"])
            finding["applicable"] = not changed and finding["fingerprints"]["status"] == "current"
            finding["changed_specifications"] = changed
        return findings


def validate_inspection(payload: dict) -> dict:
    finding = copy.deepcopy(payload)
    if not isinstance(finding, dict) or finding.get("schema_version") != 1:
        raise EvidenceError("Unsupported inspection schema; expected 1")
    if not isinstance(finding.get("inspection_id"), str) or not finding["inspection_id"]:
        raise EvidenceError("An inspection_id is required")
    if finding.get("observational") is not True or finding.get("tests_executed", False) is not False:
        raise EvidenceError("SpecViz inspections must be observational; tests cannot execute")
    if not isinstance(finding.get("complete"), bool):
        raise EvidenceError("Inspection must explicitly identify whether its scope is complete")
    if not isinstance(finding.get("scope"), list) or not finding["scope"]:
        raise EvidenceError("Inspection requires its declared scope")
    _implementation(finding.get("implementation"))
    sources = finding.get("specifications")
    if not isinstance(sources, list) or not sources:
        raise EvidenceError("Inspection requires retained specification fingerprints")
    for source in sources:
        _relative_path(source.get("path"))
        if not _hash(source.get("hash")):
            raise EvidenceError("Invalid inspected specification fingerprint")
    rows = finding.get("findings")
    if not isinstance(rows, list):
        raise EvidenceError("findings must be an array")
    for row in rows:
        if row.get("status") not in {"supported", "partial", "contradicted", "not-found", "unclear"}:
            raise EvidenceError("Invalid code-inspection status")
        if not isinstance(row.get("requirement_id"), str) or not row["requirement_id"]:
            raise EvidenceError("Inspection findings require requirement_id")
        document = _relative_path(row.get("document"))
        if document not in {s["path"] for s in sources}:
            raise EvidenceError("Inspection finding references an unbound specification")
        if not isinstance(row.get("reason"), str) or not row["reason"]:
            raise EvidenceError("Inspection findings require a source-backed explanation")
        locations = row.get("locations", [])
        if not isinstance(locations, list):
            raise EvidenceError("Inspection locations must be an array")
        for location in locations:
            path = _relative_path(location.get("path"))
            if path not in finding["implementation"].get("files", {}):
                raise EvidenceError("Inspection location lacks a retained implementation fingerprint")
            if not isinstance(location.get("line"), int) or location["line"] < 1:
                raise EvidenceError("Inspection location requires a positive source line")
        if row["status"] in {"supported", "partial", "contradicted"} and not locations:
            raise EvidenceError("Supported, partial or contradicted findings need inspected source locations")
        if not isinstance(row.get("uninspected", []), list):
            raise EvidenceError("uninspected scope must be an array")
        if row["status"] == "supported" and row.get("uninspected"):
            raise EvidenceError("Incomplete requirement inspection cannot claim full support")
        if row.get("tests", {}).get("executed", False):
            raise EvidenceError("Read test definitions do not establish an executed check")
    return finding
