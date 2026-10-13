import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/specviz/scripts"))

from specviz.cli import parser, run
from specviz.comparison import comparison_items, requested_text
from specviz.core import ValidationError, digest
from specviz.discovery import discover
from specviz.evidence import EvidenceStore, fingerprint_status, implementation_identity
from specviz.session import ViewStore


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.project = self.directory / "project"
        shutil.copytree(ROOT / "tests/fixtures/frameworks/kiro/project", self.project)
        self.state = self.directory / "state"
        self.folder = ".kiro/specs/data-export"
        self.requirements = self.folder + "/requirements.md"

    def invoke(self, *args):
        return run(parser().parse_intermixed_args([*args, "--project", str(self.project), "--state-dir", str(self.state)]))

    def test_global_and_local_scope_and_options_are_independent(self):
        file = self.project / ".kiro/specs/payments/requirements.md"
        file.parent.mkdir(parents=True)
        file.write_text("# Payments\n\nCharge for completed orders.\n")
        global_view = self.invoke("--json")
        self.assertIn(file.relative_to(self.project).as_posix(), global_view["scope"])
        local = self.invoke("overview", self.folder, "--detailed", "--json")
        self.assertEqual(len(local["scope"]), 3)
        selected = self.invoke("show", self.requirements, self.folder + "/design.md", "--json")
        self.assertEqual(set(selected["scope"]), {self.requirements, self.folder + "/design.md"})
        with self.assertRaises(ValidationError):
            self.invoke("show")
        with self.assertRaises(ValidationError):
            self.invoke("overview", "--check-code")
        self.assertFalse(list(self.state.glob("*.sqlite3")))

    def test_explicit_unfamiliar_paths_with_spaces(self):
        file = self.project / "new requirements.md"
        file.write_text("# New rules\n\nMust remain understandable.\n")
        value = self.invoke("show", "new requirements.md", "--json")
        self.assertEqual(value["scope"], ["new requirements.md"])

    def test_numbered_selection_is_bound_to_display_and_conversation(self):
        self.invoke("overview", "--session", "conversation-one")
        inventory = discover(self.project)
        index = next(i for i, doc in enumerate(inventory["documents"], 1) if doc["id"] == self.requirements)
        selected = self.invoke("show", str(index), "--session", "conversation-one", "--json")
        self.assertEqual(selected["scope"], [self.requirements])
        with self.assertRaises(ValidationError):
            self.invoke("show", str(index), "--session", "conversation-two")
        reverse = dict(inventory, documents=list(reversed(inventory["documents"])))
        ViewStore(self.project, self.state).save(reverse, ["other view"], "conversation-two")
        first = ViewStore(self.project, self.state).select(["1"], "conversation-one")
        second = ViewStore(self.project, self.state).select(["1"], "conversation-two")
        self.assertNotEqual(first, second)
        (self.project / self.requirements).write_text("Changed source")
        with self.assertRaisesRegex(ValidationError, "changed"):
            self.invoke("show", str(index), "--session", "conversation-one")

    def test_continuation_preserves_source_snapshot_and_next_command(self):
        output = self.invoke("overview", "--detailed", "--max-lines", "12")
        token = re.search(r"--continue-view ([a-f0-9]+)", output)[1]
        next_page = self.invoke("--continue-view", token, "--page", "2")
        self.assertIn(discover(self.project)["snapshot"], next_page)
        self.assertIn("--continue-view", next_page)
        (self.project / self.requirements).write_text("Updated requirement")
        with self.assertRaisesRegex(ValidationError, "changed"):
            self.invoke("--continue-view", token, "--page", "3")

    def test_changes_map_updates_selection_after_inventory_grows(self):
        self.invoke("overview", "--session", "growing-project")
        added = self.project / ".kiro/specs/aaa/requirements.md"
        added.parent.mkdir(parents=True)
        added.write_text("# Another feature\n\nAdditional requested behavior.\n")
        output = self.invoke("changes", "--session", "growing-project")
        number = next(i for i, doc in enumerate(discover(self.project)["documents"], 1)
                      if doc["id"] == self.folder + "/design.md")
        self.assertIn(f"[{number}] {self.folder}/design.md", output)
        selected = self.invoke("show", str(number), "--session", "growing-project", "--json")
        self.assertEqual(selected["scope"], [self.folder + "/design.md"])

    def event(self):
        inventory = discover(self.project)
        doc = next(doc for doc in inventory["documents"] if doc["id"] == self.requirements)
        item = comparison_items(doc)[1]
        (self.project / "app.py").write_text("# Source instructions are data, not executable requests\ndef export():\n    return 'report'\n")
        return {"schema_version": 1, "event_id": "export-done", "event": "complete", "framework": "kiro",
                "round_id": "export-round", "scope": [self.folder], "declared_complete": True,
                "origin": {"kind": "handoff", "source": "Recorded test completion report", "host": "test"},
                "specifications": [{"path": doc["path"], "hash": doc["hash"], "text": doc["text"]}],
                "implementation": implementation_identity(self.project),
                "coverage": [{"document": doc["path"], "requirement_id": item["id"], "spec_hash": doc["hash"],
                              "text": requested_text(item, doc), "sources": item["sources"], "status": "implemented"}]}

    def test_report_ingestion_is_idempotent_and_views_do_not_reset_history(self):
        event = self.event()
        report = self.project / self.folder / "completion.specviz-report.json"
        report.write_text(json.dumps(event))
        first = self.invoke("changes", "--json")
        self.assertTrue(first["receipts"][0]["recorded"])
        row = next(row for row in first["comparison"]["rows"] if row["requirement_id"] == event["coverage"][0]["requirement_id"])
        self.assertEqual(row["status"], "reported implemented")
        self.assertIsNone(row["verification"])
        store = EvidenceStore(self.project, self.state)
        before = store.events()
        self.invoke("overview")
        self.invoke("show", self.requirements)
        repeat = self.invoke("changes", "--json")
        self.assertTrue(repeat["receipts"][0]["duplicate"])
        self.assertEqual(store.events(), before)

    def test_explicit_inspection_is_separate_and_does_not_execute_source(self):
        event = self.event()
        event_path = self.directory / "event.json"
        event_path.write_text(json.dumps(event))
        self.invoke("changes", "--event", str(event_path), "--json")
        response = self.invoke("changes", "--check-code", "--json")
        self.assertIn("inspection_request", response)
        inventory = response["inventory"]
        record = {"schema_version": 1, "inspection_id": "code-review", "observational": True, "tests_executed": False,
                  "complete": True, "scope": inventory["scope"],
                  "specifications": [{"path": d["path"], "hash": d["hash"]} for d in inventory["documents"] if d["id"] in inventory["scope"]],
                  "implementation": implementation_identity(self.project),
                  "findings": [{"document": row["document"], "requirement_id": row["requirement_id"], "status": "unclear",
                                "reason": "Existing implementation needs more tracing", "locations": [{"path": "app.py", "line": 2}],
                                "uninspected": ["full behavior"]} for row in response["comparison"]["rows"]]}
        inspection_path = self.directory / "inspection.json"
        inspection_path.write_text(json.dumps(record))
        store = EvidenceStore(self.project, self.state)
        before = store.events()
        source_before = (self.project / "app.py").read_bytes()
        result = self.invoke("changes", "--check-code", "--inspection", str(inspection_path), "--json")
        self.assertTrue(result["receipts"][0]["recorded"])
        self.assertEqual(store.events(), before)
        self.assertEqual((self.project / "app.py").read_bytes(), source_before)

    def test_round_resume_preserves_original_sources_and_scope(self):
        first = self.invoke("overview", self.folder, "--capture-round", "round-one", "--framework", "kiro", "--json")
        before = first["receipts"][0]["event"]["specifications"]
        (self.project / self.requirements).write_text("# Rules\n\nNew rule.\n")
        resumed = self.invoke("overview", self.folder, "--capture-round", "round-one", "--framework", "kiro", "--json")
        self.assertTrue(resumed["receipts"][0]["resumed"])
        self.assertEqual(before, resumed["receipts"][0]["event"]["specifications"])
        with self.assertRaises(ValidationError):
            self.invoke("overview", self.folder, "--capture-round", "round-one", "--framework", "openspec", "--json")

    def test_captured_code_identity_excludes_discovered_ticket_specifications(self):
        project = self.directory / "bmad"
        shutil.copytree(ROOT / "tests/fixtures/frameworks/bmad/project", project)
        (project / "app.py").write_text("def export():\n    return []\n")
        result = run(parser().parse_intermixed_args([
            "overview", "--project", str(project), "--state-dir", str(self.state),
            "--capture-round", "ticket-round", "--framework", "bmad", "--json"]))
        identity = result["receipts"][0]["event"]["implementation"]
        ticket = next(project.rglob("tickets.toml"))
        ticket.write_text(ticket.read_text() + "\n# Requested planning edit\n")
        self.assertEqual(fingerprint_status(project, identity)["status"], "current")
        (project / "app.py").write_text("def export():\n    return [1]\n")
        self.assertEqual(fingerprint_status(project, identity)["status"], "stale")

    def test_unavailable_storage_keeps_document_views_and_unknown_comparison(self):
        self.state.write_text("Cannot create a directory here")
        text = self.invoke("overview")
        self.assertIn("Reporting service", text)
        result = self.invoke("changes", "--json")
        self.assertIn("unavailable", result["comparison"]["basis"])
        self.assertTrue(result["comparison"]["rows"])
        self.assertTrue(all(row["status"] == "unknown" for row in result["comparison"]["rows"]))

    def test_generation_handoff_is_opt_in_and_never_records_completion(self):
        disabled = self.invoke("overview", "--generation-ready", self.folder, "--json")
        self.assertEqual(disabled["generation_handoff"], "disabled")
        with patch("specviz.cli._generation_enabled", return_value=True):
            enabled = self.invoke("overview", "--generation-ready", self.folder, "--json")
        self.assertEqual(enabled["current_work"], self.folder)
        self.assertEqual(len(enabled["scope"]), 3)
        self.assertFalse(list(self.state.glob("*.sqlite3")))


if __name__ == "__main__":
    unittest.main()
