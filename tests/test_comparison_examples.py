"""Executable examples preserve scoped reports and conflicting observations."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.comparison import compare, requested_text
from specviz.core import default_items, digest, parse_blocks, snapshot_file
from specviz.evidence import EvidenceStore, implementation_identity
from specviz.render import render_changes

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "comparison"
PROJECT = EXAMPLE / "project"


def example_outputs():
    documents = [snapshot_file(PROJECT / path, PROJECT) for path in ("requirements.md", "design.md", "tasks.md")]
    for document in documents:
        document["group"] = "data-export"
    inventory = {"schema_version": 1, "project": {"root": str(PROJECT.resolve()), "name": "Reporting service", "purpose": "Create downloadable reports"},
                 "snapshot": digest("".join(doc["hash"] for doc in documents)), "documents": documents,
                 "groups": [{"id": "data-export", "label": "Data export", "purpose": "Create and protect report files"}],
                 "relationships": [{"from": "requirements.md", "to": "design.md", "type": "workflow", "label": "Rules inform design"},
                                   {"from": "design.md", "to": "tasks.md", "type": "workflow", "label": "Design informs implementation steps"}],
                 "warnings": [], "scope": [doc["id"] for doc in documents], "context": []}
    model = {"schema_version": 1, "snapshot": inventory["snapshot"],
             "project": {"purpose": "Create downloadable reports"},
             "documents": [{"id": doc["id"], "purpose": {"requirements.md": "Export rules", "design.md": "Export protection", "tasks.md": "Implementation checklist"}[doc["id"]],
                            "items": default_items(doc)} for doc in documents]}
    outputs = {}
    for mode in ("reports", "code-inspection"):
        with tempfile.TemporaryDirectory() as state:
            store = EvidenceStore(PROJECT, Path(state))
            versions = []
            coverage = []
            for document in documents:
                source = dict(document)
                if mode == "reports" and document["id"] == "design.md":
                    source["text"] = "# Export design\n\nCreate a downloadable file.\n"
                if mode == "reports" and document["id"] == "tasks.md":
                    source["text"] = "# Implementation steps\n\n- [x] Create report files.\n"
                source["hash"] = digest(source["text"])
                source["blocks"] = parse_blocks(source["text"], source["id"])
                versions.append({"path": source["path"], "hash": source["hash"], "text": source["text"]})
                item = default_items(source)[0]
                coverage.append({"requirement_id": item["id"], "document": source["path"], "spec_hash": source["hash"],
                                 "text": requested_text(item, source), "sources": item["sources"], "status": "implemented"})
            event_id = "fictional-export-report-" + mode
            event = {"schema_version": 1, "event_id": event_id, "event": "complete", "framework": "openspec",
                     "round_id": "fictional-export-round-" + mode, "scope": ["Data export"],
                     "occurred_at": "2026-10-12T00:00:00+00:00" if mode == "reports" else "2026-10-12T01:00:00+00:00",
                     "origin": {"kind": "handoff", "source": "Fictional completion report for this example", "host": "codex"},
                     "specifications": versions, "implementation": implementation_identity(PROJECT, ["export.py"]),
                     "coverage": coverage, "declared_complete": True}
            outputs["report.json" if mode == "reports" else "conflicting-report.json"] = json.dumps(event, indent=2) + "\n"
            store.ingest(event)
            interpreted = dict(model)
            if mode == "reports":
                interpreted["comparisons"] = []
                for current, previous in zip(documents, coverage):
                    if current["id"] not in {"design.md", "tasks.md"}:
                        continue
                    item = default_items(current)[0]
                    interpreted["comparisons"].append({"document": current["id"], "requirement_id": item["id"],
                                                       "evidence_id": event_id, "classification": "behavioral",
                                                       "sources": item["sources"], "prior_text": previous["text"],
                                                       "reason": "Password protection adds a requested obligation to earlier file creation"})
            else:
                findings = []
                for document in documents:
                    item = default_items(document)[0]
                    status, reason, line = {"requirements.md": ("partial", "Plain export returns a filename; file creation and delivery are not established", 7),
                                           "design.md": ("contradicted", "The password guard raises an error instead of protecting the file", 6),
                                           "tasks.md": ("partial", "An export function returns a filename; file creation and password protection remain unfinished", 5)}[document["id"]]
                    findings.append({"document": document["id"], "requirement_id": item["id"], "status": status,
                                     "reason": reason, "locations": [{"path": "export.py", "line": line}],
                                     "uninspected": ["File creation and delivery beyond the returned filename"] if status == "partial" else [],
                                     "tests": {"executed": False, "definitions": ["test_export.py:6"]}})
                inspection = {"schema_version": 1, "inspection_id": "fictional-code-inspection",
                                       "observational": True, "tests_executed": False, "complete": True, "scope": inventory["scope"],
                                       "specifications": [{"path": doc["path"], "hash": doc["hash"]} for doc in documents],
                                       "implementation": implementation_identity(PROJECT, ["export.py", "test_export.py"]), "findings": findings}
                outputs["inspection.json"] = json.dumps(inspection, indent=2) + "\n"
                store.save_inspection(inspection)
            comparison = compare(inventory, store, interpreted, use_inspections=mode == "code-inspection")
            for row in comparison["rows"]:
                if row["evidence"]:
                    row["evidence"]["recorded_at"] = "2026-10-12T00:00:00+00:00"
            for detailed in (False, True):
                name = mode + ("-detailed" if detailed else "") + ".txt"
                outputs[name] = render_changes(inventory, comparison, interpreted, detailed)
    return outputs


class ComparisonExampleTests(unittest.TestCase):
    def test_maintained_examples_match_source_backed_outputs(self):
        before = {path.name: digest(path.read_bytes()) for path in PROJECT.iterdir() if path.is_file()}
        outputs = example_outputs()
        for name, text in outputs.items():
            with self.subTest(name=name):
                self.assertEqual((EXAMPLE / name).read_text(encoding="utf-8"), text)
                if name.endswith(".json"):
                    self.assertNotIn("project", json.loads(text))
                    continue
                self.assertIn("Data export", text)
                self.assertIn("Verification:", text)
                self.assertIn("requirements.md", text)
                self.assertIn("design.md", text)
                self.assertIn("tasks.md", text)
        self.assertIn("[contains changes] Data export", outputs["reports.txt"])
        self.assertIn("contradicted", outputs["code-inspection.txt"])
        self.assertIn("Fictional completion report", outputs["code-inspection-detailed.txt"])
        self.assertIn("tests were not executed", outputs["code-inspection-detailed.txt"])
        self.assertEqual(before, {path.name: digest(path.read_bytes()) for path in PROJECT.iterdir() if path.is_file()})

    def test_persisted_report_inputs_work_in_a_copied_project(self):
        from specviz.cli import main
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "project"
            shutil.copytree(PROJECT, copied)
            state = Path(temporary) / "state"
            report = json.loads((EXAMPLE / "report.json").read_text())
            store = EvidenceStore(copied, state)
            store.ingest(report)
            self.assertEqual(store.events()[0]["project"]["root"], str(copied.resolve()))
            with redirect_stdout(io.StringIO()) as captured:
                result = main(["changes", "requirements.md", "design.md", "tasks.md", "--project", str(copied),
                               "--reports", str(EXAMPLE / "report.json"), "--state-dir", str(state), "--max-lines", "200"])
            self.assertEqual(result, 0)
            self.assertIn("Export design", captured.getvalue())
            self.assertIn("reported", captured.getvalue().lower())
            self.assertEqual(len(store.events()), 1)


if __name__ == "__main__":
    if "--write-goldens" in sys.argv:
        for name, text in example_outputs().items():
            (EXAMPLE / name).write_text(text, encoding="utf-8")
    else:
        unittest.main()
