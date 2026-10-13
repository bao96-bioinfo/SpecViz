"""Evidence is scoped history, never a checkbox-based compliance assertion."""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.evidence import (EvidenceError, EvidenceStore, PersistenceError,
                             digest, fingerprint_status, implementation_identity,
                             normalize_handoff, validate_event, validate_inspection)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / "export.py").write_text("def export(): return 'file'\n", encoding="utf-8")
        (self.project / "requirements.md").write_text("# Export\nCreate export files.\n", encoding="utf-8")
        self.state = self.base / "state"
        self.store = EvidenceStore(self.project, self.state)

    def event(self, event_id="event-1", event="complete", framework="openspec", round_id="round-1"):
        text = (self.project / "requirements.md").read_text(encoding="utf-8")
        return {"schema_version": 1, "event_id": event_id, "event": event,
                "framework": framework, "round_id": round_id, "scope": ["Data export"],
                "origin": {"kind": "handoff", "source": "chat:completion-1", "host": "codex"},
                "specifications": [{"path": "requirements.md", "text": text, "hash": digest(text)}],
                "implementation": implementation_identity(self.project, ["export.py"]),
                "coverage": [{"requirement_id": "export", "document": "requirements.md",
                              "spec_hash": digest(text), "text": "Create export files.", "status": "implemented"}],
                "declared_complete": event == "complete"}

    def inspection(self):
        return {"schema_version": 1, "inspection_id": "inspection-1", "observational": True,
                "tests_executed": False, "complete": True, "scope": ["Data export"],
                "specifications": [{"path": "requirements.md", "hash": digest((self.project / "requirements.md").read_text())}],
                "implementation": implementation_identity(self.project, ["export.py"]),
                "findings": [{"requirement_id": "export", "document": "requirements.md", "status": "supported",
                              "reason": "Export produces the documented file", "locations": [{"path": "export.py", "line": 1}],
                              "uninspected": []}]}

    def test_same_checkout_shared_but_copies_and_worktrees_isolated(self):
        self.store.ingest(self.event())
        other_host = EvidenceStore(self.project, self.state)
        self.assertEqual(len(other_host.events()), 1)
        another = self.base / "worktree"
        another.mkdir()
        (another / ".git").write_text("gitdir: /repository/.git/worktrees/another")
        self.assertEqual(EvidenceStore(another, self.state).events(), [])
        self.assertNotEqual(other_host.path, EvidenceStore(another, self.state).path)

    def test_environment_state_relocation_and_no_tracked_state(self):
        with patch.dict(os.environ, {"SPECVIZ_STATE_DIR": str(self.base / "relocated")}):
            relocated = EvidenceStore(self.project)
        self.assertEqual(relocated.path.parent, self.base / "relocated")
        self.assertFalse(relocated.path.is_relative_to(self.project))
        with self.assertRaises(PersistenceError):
            EvidenceStore(self.project, self.project / "state")

    def test_duplicate_delivery_is_idempotent_and_conflicts_rejected(self):
        event = self.event()
        self.assertTrue(self.store.ingest(event)["recorded"])
        self.assertTrue(self.store.ingest(event)["duplicate"])
        changed = copy.deepcopy(event)
        changed["coverage"][0]["status"] = "partial"
        with self.assertRaises(EvidenceError):
            self.store.ingest(changed)
        self.assertEqual(len(self.store.events()), 1)

    def test_concurrent_delivery_records_only_one_complete_event(self):
        event = self.event()
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: EvidenceStore(self.project, self.state).ingest(event), range(6)))
        self.assertEqual(sum(result["recorded"] for result in results), 1)
        self.assertEqual(len(self.store.events()), 1)

    def test_malformed_update_and_failed_transaction_preserve_history(self):
        self.store.ingest(self.event())
        malformed = self.event("second", round_id="round-2")
        malformed["specifications"][0]["hash"] = "0" * 64
        with self.assertRaises(EvidenceError):
            self.store.ingest(malformed)
        with sqlite3.connect(self.store.path) as db:
            db.execute("CREATE TRIGGER reject_events BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'interrupted'); END")
        with self.assertRaises(PersistenceError):
            self.store.ingest(self.event("third", round_id="round-3"))
        self.assertEqual(len(self.store.events()), 1)

    def test_schema_failure_does_not_overwrite_existing_history(self):
        self.store.ingest(self.event())
        with sqlite3.connect(self.store.path) as db:
            db.execute("PRAGMA user_version=999")
        with self.assertRaises(PersistenceError):
            EvidenceStore(self.project, self.state)
        with sqlite3.connect(self.store.path) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events").fetchone()[0], 1)

    def test_unavailable_storage_is_actionable(self):
        blocked = self.base / "blocked"
        blocked.write_text("file")
        with self.assertRaisesRegex(PersistenceError, "Cannot open"):
            EvidenceStore(self.project, blocked)

    def test_begin_pause_resume_and_partial_progress_share_round(self):
        begin = self.event("begin", "begin")
        begin["coverage"] = []
        self.store.ingest(begin)
        progress = self.event("progress", "progress")
        progress["specifications"] = []  # Explicit hash binds to captured begin content.
        progress["coverage"][0]["status"] = "partial"
        self.store.ingest(progress)
        self.assertEqual(self.store.latest("export")["coverage"]["status"], "partial")
        self.assertFalse(any(event["event"] == "complete" for event in self.store.events()))
        self.store.ingest(self.event("resume", "begin"))
        self.store.ingest(self.event("done"))
        self.assertEqual({event["round_id"] for event in self.store.events()}, {"round-1"})
        with self.assertRaises(EvidenceError):
            self.store.ingest(self.event("resume-complete", "begin"))

    def test_mid_round_edits_do_not_rebind_older_implementation(self):
        begin = self.event("begin", "begin")
        begin["coverage"] = []
        self.store.ingest(begin)
        completion = self.event("done")
        completion["specifications"] = []
        (self.project / "requirements.md").write_text("# Export\nCreate password protected export files.\n")
        self.store.ingest(completion)
        latest = self.store.latest("export")
        self.assertTrue(latest["coverage"]["version_bound"])
        self.assertEqual(latest["coverage"]["text"], "Create export files.")
        self.assertEqual(latest["fingerprints"]["status"], "current")

    def test_late_report_missing_versions_is_unknown_not_current_snapshot(self):
        report = self.event()
        report["specifications"] = []
        report["coverage"][0].pop("spec_hash")
        self.store.ingest(report)
        coverage = self.store.latest("export")["coverage"]
        self.assertFalse(coverage["version_bound"])
        self.assertNotIn("specification", coverage)

    def test_invented_coverage_source_rejected_and_noncontiguous_text_bound(self):
        from specviz.core import parse_blocks
        from specviz.comparison import requested_text
        text = "# Export\n\nCreate export files.\n\nKeep audit events.\n\nReject invalid formats.\n"
        (self.project / "requirements.md").write_text(text)
        blocks = parse_blocks(text, "requirements.md")
        event = self.event()
        event["coverage"][0]["sources"] = [blocks[1]["id"], blocks[3]["id"]]
        event["coverage"][0]["text"] = requested_text(event["coverage"][0], {"text": text, "blocks": blocks})
        self.store.ingest(event)
        self.assertTrue(self.store.latest("export")["coverage"]["version_bound"])
        invented = self.event("invented", round_id="round-2")
        invented["coverage"][0]["sources"] = ["requirements.md:L900-901"]
        with self.assertRaises(EvidenceError):
            self.store.ingest(invented)

    def test_completion_and_verification_are_separate(self):
        self.store.ingest(self.event())
        self.assertIsNone(self.store.latest("export")["verification"])
        verify = self.event("verification", "verify")
        verify["coverage"] = []
        verify["verification"] = {"executed": True, "checks": [{"command": "python -m unittest", "result": "passed"}]}
        self.store.ingest(verify)
        self.assertTrue(self.store.latest("export")["verification"]["executed"])
        self.assertEqual(len([event for event in self.store.events() if event["event"] == "complete"]), 1)

    def test_late_older_report_uses_workflow_time_instead_of_delivery_order(self):
        older = self.event("older", round_id="round-older")
        older["occurred_at"] = "2026-10-11T00:00:00Z"
        newer = self.event("newer", round_id="round-newer")
        newer["occurred_at"] = "2026-10-12T01:00:00+01:00"
        self.store.ingest(newer)
        self.store.ingest(older)
        self.assertEqual(self.store.latest("export")["event"]["event_id"], "newer")
        self.assertEqual(self.store.latest("export")["chronology"], "workflow time")
        malformed = self.event("invalid-time", round_id="round-invalid")
        malformed["occurred_at"] = "2026-10-12"  # No timezone or actual workflow time.
        with self.assertRaises(EvidenceError):
            self.store.ingest(malformed)

    def test_code_fingerprints_cover_dirty_changes_deletions_and_new_sources(self):
        relevant = implementation_identity(self.project, ["export.py"])
        conservative = implementation_identity(self.project)
        (self.project / "another.py").write_text("value = 1")
        self.assertEqual(fingerprint_status(self.project, relevant)["status"], "current")
        self.assertEqual(fingerprint_status(self.project, conservative)["status"], "stale")
        (self.project / "export.py").write_text("def export(): return None")
        self.assertEqual(fingerprint_status(self.project, relevant)["status"], "stale")
        (self.project / "export.py").unlink()
        self.assertEqual(fingerprint_status(self.project, relevant)["status"], "stale")

    def test_persisted_handoff_does_not_invalidate_conservative_code_manifest(self):
        conservative = implementation_identity(self.project)
        (self.project / "export.specviz-report.json").write_text(json.dumps(self.event()))
        self.assertEqual(fingerprint_status(self.project, conservative)["status"], "current")

    def test_capture_excludes_declared_specs_from_explicit_and_conservative_manifests(self):
        specification = self.project / "tickets.toml"
        specification.write_text('goal = "Export files"\n')
        for relevant in (None, ["export.py", "requirements.md", "tickets.toml"]):
            identity = implementation_identity(self.project, relevant, ["requirements.md", "tickets.toml"])
            self.assertNotIn("requirements.md", identity["files"])
            self.assertNotIn("tickets.toml", identity["files"])
            self.assertIn("export.py", identity["files"])
            specification.write_text('goal = "Protected export files"\n')
            self.assertEqual(fingerprint_status(self.project, identity)["status"], "current")

    def test_legacy_mixed_fingerprints_ignore_bound_spec_drift_without_changing_record(self):
        event = self.event()
        event["implementation"] = implementation_identity(self.project, ["export.py", "requirements.md"])
        self.store.ingest(event)
        original = self.store.events()
        (self.project / "requirements.md").write_text("# Export\nCreate protected export files.\n")
        self.assertEqual(self.store.latest("export")["fingerprints"]["status"], "current")
        self.assertEqual(self.store.events(), original)
        (self.project / "export.py").write_text("def export(): return None")
        self.assertEqual(self.store.latest("export")["fingerprints"]["status"], "stale")

    def test_external_spec_inspection_limitation_is_explicit(self):
        finding = self.inspection()
        finding["specifications"][0]["path"] = "external::/declared/specs/requirements.md"
        finding["findings"][0]["document"] = "external::/declared/specs/requirements.md"
        with self.assertRaisesRegex(EvidenceError, "external specification sources is unsupported"):
            self.store.save_inspection(finding)

    def test_scope_and_project_mismatch_rejected(self):
        self.store.ingest(self.event("begin", "begin"))
        wrong_scope = self.event()
        wrong_scope["scope"] = ["Payments"]
        with self.assertRaises(EvidenceError):
            self.store.ingest(wrong_scope)
        wrong_project = self.event()
        wrong_project["project"] = {"id": "different"}
        with self.assertRaises(EvidenceError):
            self.store.ingest(wrong_project)

    def test_all_framework_handoff_fixtures_retain_origin_and_versions(self):
        fixture_root = Path(__file__).parent / "fixtures" / "reports"
        for framework in ("openspec", "spec-kit", "bmad", "superpowers", "kiro"):
            with self.subTest(framework=framework):
                payload = json.loads((fixture_root / (framework + ".json")).read_text())
                normalized = normalize_handoff(framework, payload)
                self.assertEqual(normalized["origin"]["kind"], "handoff")
                self.assertEqual(normalized["framework"], framework)
                self.assertEqual(normalized["specifications"][0]["hash"], digest(normalized["specifications"][0]["text"]))
                self.assertTrue(normalized.get("fixture_provenance", {}).get("source"))

    def test_bmad_built_not_complete_and_native_tasklists_not_supported(self):
        built = self.event(framework="bmad")
        built["workflow_status"] = "built"
        with self.assertRaises(EvidenceError):
            normalize_handoff("bmad", built)
        built["event"] = "progress"
        self.assertEqual(normalize_handoff("bmad", built)["event"], "progress")
        native = self.event()
        native["origin"] = {"kind": "native-report", "source": "tasks.md", "format": "task-list"}
        with self.assertRaises(EvidenceError):
            self.store.ingest(native)

    def test_inspections_do_not_modify_workflow_history_and_go_stale(self):
        self.store.ingest(self.event())
        before = self.store.events()
        finding = self.inspection()
        self.assertTrue(self.store.save_inspection(finding)["recorded"])
        self.assertTrue(self.store.save_inspection(finding)["duplicate"])
        self.assertEqual(before, self.store.events())
        self.assertTrue(self.store.inspections()[0]["applicable"])
        (self.project / "export.py").write_text("def export(): return None")
        self.assertFalse(self.store.inspections()[0]["applicable"])

    def test_inspection_spec_changes_and_missing_code_cannot_reuse_confirmation(self):
        self.store.save_inspection(self.inspection())
        (self.project / "requirements.md").write_text("# Export\nExport only protected files.")
        finding = self.store.inspections()[0]
        self.assertFalse(finding["applicable"])
        self.assertEqual(finding["changed_specifications"], ["requirements.md"])
        with self.assertRaises(EvidenceError):
            self.store.save_inspection(self.inspection() | {"implementation": {"files": {}}})

    def test_inspection_fingerprints_preserve_crlf_and_bom_bytes(self):
        raw = b"\xef\xbb\xbf# Export\r\nCreate export files.\r\n"
        (self.project / "requirements.md").write_bytes(raw)
        finding = self.inspection()
        finding["specifications"][0]["hash"] = hashlib.sha256(raw).hexdigest()
        self.store.save_inspection(finding)
        self.assertTrue(self.store.inspections()[0]["applicable"])

    def test_incomplete_inspection_and_test_presence_are_not_passing_verification(self):
        finding = self.inspection()
        finding["complete"] = False
        finding["findings"][0]["status"] = "partial"
        finding["findings"][0]["uninspected"] = ["Invalid format handling"]
        finding["findings"][0]["tests"] = {"executed": False, "definitions": ["tests/test_export.py"]}
        self.store.save_inspection(finding)
        self.assertFalse(self.store.inspections()[0]["complete"])
        finding["findings"][0]["tests"]["executed"] = True
        with self.assertRaises(EvidenceError):
            validate_inspection(finding)

    def test_inspection_rejects_invented_locations_and_active_commands(self):
        for mutation in (lambda p: p.update(observational=False),
                         lambda p: p.update(tests_executed=True),
                         lambda p: p["findings"][0]["locations"][0].update(path="missing.py")):
            finding = self.inspection()
            mutation(finding)
            with self.assertRaises(EvidenceError):
                self.store.save_inspection(finding)


if __name__ == "__main__":
    unittest.main()
