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

    def test_overview_hint_suppression_changes_only_the_generic_footer(self):
        hint = "Use show <file number or path> to explore a file; add --detailed to expand it."
        for arguments in ([], ["overview"], ["overview", self.folder, "--detailed"]):
            with self.subTest(arguments=arguments):
                ordinary = self.invoke(*arguments, "--max-lines", "2000")
                contextual = self.invoke(*arguments, "--max-lines", "2000", "--omit-overview-hint")
                self.assertIn(hint, ordinary)
                self.assertEqual(contextual, ordinary.removesuffix("\n" + hint + "\n").rstrip() + "\n")
                self.assertEqual(self.invoke(*arguments, "--json"),
                                 self.invoke(*arguments, "--json", "--omit-overview-hint"))
        inventory = discover(self.project)
        inventory["warnings"].append("A declared source could not be read.")
        with patch("specviz.cli.discover", return_value=inventory):
            output = self.invoke("--omit-overview-hint", "--max-lines", "2000")
        self.assertIn("A declared source could not be read.", output)
        for action in ("show", "changes"):
            with self.assertRaisesRegex(ValidationError, "only for overview"):
                self.invoke(action, self.requirements, "--omit-overview-hint", "--json")

    def test_suppressed_hint_keeps_empty_scope_recovery_and_generation_handoff(self):
        empty = self.project / "empty"
        empty.mkdir()
        arguments = ["--project", str(empty), "--state-dir", str(self.state)]
        ordinary = run(parser().parse_args(arguments))
        self.assertEqual(ordinary, run(parser().parse_args([*arguments, "--omit-overview-hint"])))
        self.assertIn("No specification files found in this scope.", ordinary)
        self.assertIn("check the project path", ordinary)
        with patch("specviz.cli._generation_enabled", return_value=True):
            output = self.invoke("--generation-ready", self.folder, "--omit-overview-hint", "--max-lines", "2000")
        self.assertIn("Reporting service", output)
        self.assertIn("requirements.md", output)
        self.assertNotIn("Use show <file number or path>", output)
        self.assertFalse(list(self.state.glob("*.sqlite3")))

    def test_suppressed_hint_preserves_complete_delivery_selections_and_evidence(self):
        store = EvidenceStore(self.project, self.state)
        store.ingest(self.event())
        evidence = store.events()
        sources = {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        output = self.invoke("overview", "--detailed", "--max-lines", "12",
                             "--session", "contextual-reader", "--omit-overview-hint")
        token = re.search(r"--continue-view ([a-f0-9]+)", output)[1]
        views = ViewStore(self.project, self.state)
        saved = views.load(token)
        with self.assertRaisesRegex(ValidationError, "not been exposed"):
            views.select(["1"], "contextual-reader")
        with self.assertRaisesRegex(ValidationError, "another conversation"):
            self.invoke("--continue-view", token, "--page", "2", "--session", "other-reader")
        delivered = [output]
        for page in range(2, len(saved["pages"]) + 1):
            delivered.append(self.invoke("--continue-view", token, "--page", str(page), "--session", "contextual-reader"))
        self.assertNotIn("Use show <file number or path>", "".join(delivered))
        self.assertIn("End of this view.", delivered[-1])
        self.assertNotIn("--continue-view", delivered[-1])
        self.assertEqual(views.load(token)["pages"], saved["pages"])
        self.assertEqual(views.load(token)["snapshot"], discover(self.project)["snapshot"])
        for number, identity in enumerate(saved["selection"], 1):
            self.assertEqual(views.select([str(number)], "contextual-reader"), [identity])
        self.assertEqual(store.events(), evidence)
        self.assertEqual(sources, {p: p.read_bytes() for p in self.project.rglob("*") if p.is_file()})

    def test_suppressed_hint_preserves_unavailable_storage_and_legacy_pages(self):
        for failure in (patch("specviz.cli.ViewStore", side_effect=OSError("Read-only state")),
                        patch.object(ViewStore, "_write", side_effect=OSError("Read-only state"))):
            with failure:
                output = self.invoke("--omit-overview-hint", "--max-lines", "12")
            self.assertIn("Select files by path.", output)
            self.assertIn("Read-only state", output)
            self.assertNotIn("Use show <file number or path>", output)
            self.assertNotIn("--continue-view", output)
            for doc in discover(self.project)["documents"]:
                self.assertIn(Path(doc["path"]).name, output)
        views = ViewStore(self.project, self.state)
        last_page = "Legacy page\nUse show <file number or path> to explore a file; add --detailed to expand it.\n"
        token = views.save(discover(self.project), ["First page\n", last_page], "legacy-reader")
        self.assertEqual(self.invoke("--continue-view", token, "--page", "2", "--omit-overview-hint"), last_page)
        self.assertEqual(views.load(token)["pages"][-1], last_page)
        self.assertFalse(list(self.state.glob("*.sqlite3")))

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
        self.assertEqual(discover(self.project)["snapshot"], ViewStore(self.project, self.state).load(token)["snapshot"])
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
        self.assertIn(f"[{number}] design.md", output)
        selected = self.invoke("show", str(number), "--session", "growing-project", "--json")
        self.assertEqual(selected["scope"], [self.folder + "/design.md"])

    def test_only_delivered_file_keys_enable_numbers_in_their_conversation(self):
        output = self.invoke("overview", "--max-lines", "12", "--session", "paged-reader")
        token = re.search(r"--continue-view ([a-f0-9]+)", output)[1]
        store = ViewStore(self.project, self.state)
        saved = store.load(token)
        self.assertEqual(saved["visible"], [])
        with self.assertRaisesRegex(ValidationError, "not been exposed"):
            store.select(["1"], "paged-reader")
        with self.assertRaisesRegex(ValidationError, "another conversation"):
            self.invoke("--continue-view", token, "--page", "2", "--session", "someone-else")
        identity = saved["selection"][0]
        for page in saved["document_pages"][identity]:
            self.invoke("--continue-view", token, "--page", str(page), "--session", "paged-reader")
        self.assertEqual(store.select(["1"], "paged-reader"), [identity])
        self.assertEqual(store.load(token)["pages"], saved["pages"])
        self.assertFalse(list(self.state.glob("*.sqlite3")))

    def test_split_file_key_requires_all_of_its_pages(self):
        inventory = discover(self.project)
        identity = inventory["documents"][0]["id"]
        store = ViewStore(self.project, self.state)
        token = store.save(inventory, ["Directory prefix", "[1] exact file key"], "split-key",
                           [[identity], [identity]], initial_page=2)
        with self.assertRaisesRegex(ValidationError, "not been exposed"):
            store.select(["1"], "split-key")
        store.deliver(token, 1, "split-key")
        self.assertEqual(store.select(["1"], "split-key"), [identity])

    def test_legacy_saved_pages_remain_readable_and_do_not_record_evidence(self):
        inventory = discover(self.project)
        store = ViewStore(self.project, self.state)
        token = store.save(inventory, ["Legacy page one\n", "Legacy page two\n"], "legacy-reader")
        self.assertEqual(self.invoke("--continue-view", token, "--page", "2"), "Legacy page two\n")
        self.assertNotIn("document_pages", store.load(token))
        self.assertEqual(store.select(["1"], "legacy-reader"), [inventory["documents"][0]["id"]])
        self.assertFalse(list(self.state.glob("*.sqlite3")))

    def test_storage_failure_exposes_complete_view_and_continuation_remains_readable(self):
        with patch.object(ViewStore, "_write", side_effect=OSError("Read-only state")):
            output = self.invoke("overview", "--max-lines", "12")
        self.assertIn("showing the complete view", output.casefold())
        for doc in discover(self.project)["documents"]:
            self.assertIn(Path(doc["path"]).name, output)
        self.assertNotIn("--continue-view", output)
        output = self.invoke("overview", "--max-lines", "12", "--session", "reader")
        token = re.search(r"--continue-view ([a-f0-9]+)", output)[1]
        with patch.object(ViewStore, "_write", side_effect=OSError("Read-only state")):
            continued = self.invoke("--continue-view", token, "--page", "2", "--session", "reader")
            self.assertIn("View part 2/", continued)
            self.assertIn("select newly shown files by path", continued)
        self.assertFalse(list(self.state.glob("*.sqlite3")))

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
