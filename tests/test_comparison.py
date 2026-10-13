import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.comparison import compare, requested_text
from specviz.core import default_items, digest, snapshot_file
from specviz.evidence import EvidenceError, EvidenceStore, implementation_identity


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / "project"
        self.project.mkdir()
        (self.project / "export.py").write_text("def export(): return 'file'\n", encoding="utf-8")
        self.path = self.project / "requirements.md"
        self.path.write_text("# Export rules\n\nCreate export files.\n", encoding="utf-8")
        self.store = EvidenceStore(self.project, self.base / "state")

    def inventory(self, paths=None):
        documents = [snapshot_file(path, self.project) for path in (paths or [self.path])]
        return {"schema_version": 1, "project": {"root": str(self.project), "name": "Reporting service"},
                "snapshot": digest("".join(doc["hash"] for doc in documents)), "documents": documents,
                "groups": [], "relationships": [], "warnings": [], "scope": [doc["id"] for doc in documents], "context": []}

    def event(self, event_id="complete-1", status="implemented", round_id="round-1", path=None):
        doc = snapshot_file(path or self.path, self.project)
        item = default_items(doc)[0]
        return {"schema_version": 1, "event_id": event_id, "event": "complete", "framework": "openspec",
                "round_id": round_id, "scope": ["Data export"], "origin": {"kind": "handoff", "source": "chat:completion"},
                "occurred_at": f"2026-10-12T{int(round_id[-1]) if round_id[-1].isdigit() else 0:02d}:00:00+00:00",
                "specifications": [{"path": doc["path"], "hash": doc["hash"], "text": doc["text"]}],
                "implementation": implementation_identity(self.project, ["export.py"]),
                "coverage": [{"requirement_id": item["id"], "document": doc["path"], "spec_hash": doc["hash"],
                              "text": requested_text(item, doc), "sources": item["sources"], "status": status}], "declared_complete": True}

    def model(self, inventory, classification="equivalent", evidence_id="complete-1", prior_event=None):
        event = prior_event or self.store.events()[0]
        current = inventory["documents"][0]
        item = default_items(current)[0]
        coverage = event["coverage"][0]
        return {"schema_version": 1, "snapshot": inventory["snapshot"],
                "documents": [{"id": current["id"], "purpose": "Export rules", "items": default_items(current)}],
                "comparisons": [{"document": current["id"], "requirement_id": item["id"],
                                 "classification": classification, "evidence_id": evidence_id,
                                 "evidence_requirement_id": coverage["requirement_id"], "evidence_document": coverage["document"],
                                 "sources": item["sources"], "prior_text": coverage["text"],
                                 "reason": "Conditions and outcomes are source-backed and reviewed"}]}

    def test_missing_reports_unknown_and_display_does_not_change_history(self):
        inventory = self.inventory()
        result = compare(inventory, self.store)
        self.assertEqual(result["rows"][0]["status"], "unknown")
        self.assertIn("--check-code", result["rows"][0]["reason"])
        self.assertEqual(compare(inventory, self.store), result)
        self.assertEqual(self.store.events(), [])

    def test_valid_earlier_implementation_remains_reference_after_spec_edit(self):
        self.store.ingest(self.event())
        self.path.write_text("# Export rules\n\nCreate password protected export files.\n")
        inventory = self.inventory()
        result = compare(inventory, self.store, self.model(inventory, "behavioral"))
        row = result["rows"][0]
        self.assertEqual(row["status"], "reported implemented")
        self.assertEqual(row["difference"], "behavioral")
        self.assertEqual(row["implemented"], "# Export rules\n\nCreate export files.")
        self.assertIn("password protected", row["requested"])
        self.assertIsNone(row["verification"])

    def test_new_completion_clears_only_covered_feature(self):
        other = self.project / "payments.md"
        other.write_text("# Payments\n\nProcess payments.\n")
        self.store.ingest(self.event())
        self.path.write_text("# Export rules\n\nCreate protected export files.\n")
        self.store.ingest(self.event("complete-2", round_id="round-2"))
        rows = compare(self.inventory([self.path, other]), self.store)["rows"]
        export = next(row for row in rows if row["document"] == "requirements.md")
        payments = next(row for row in rows if row["document"] == "payments.md")
        self.assertEqual(export["difference"], "unchanged")
        self.assertEqual(export["status"], "reported implemented")
        self.assertEqual(payments["status"], "unknown")

    def test_partial_coverage_never_implies_combined_completion(self):
        self.store.ingest(self.event(status="partial"))
        row = compare(self.inventory(), self.store)["rows"][0]
        self.assertEqual(row["status"], "partial")
        self.assertIn("only part", row["reason"])

    def test_new_limited_progress_does_not_erase_earlier_valid_reference(self):
        self.store.ingest(self.event())
        progress = self.event("progress-2", "task-progress", "round-2")
        progress["event"] = "progress"
        progress["specifications"] = []
        progress["coverage"][0].pop("spec_hash")
        self.store.ingest(progress)
        result = compare(self.inventory(), self.store)
        self.assertEqual(result["rows"][0]["status"], "reported implemented")
        self.assertTrue(result["warnings"])

    def test_newer_partial_behavior_remains_partial_with_reported_portions(self):
        self.store.ingest(self.event())
        self.path.write_text("# Export rules\n\nCreate protected export files; reject invalid formats.\n")
        partial = self.event("partial-2", "partial", "round-2")
        partial["coverage"][0]["details"] = {"implemented": "Protected creation", "outstanding": "Invalid-format rejection"}
        self.store.ingest(partial)
        row = compare(self.inventory(), self.store)["rows"][0]
        self.assertEqual(row["status"], "partial")
        self.assertIn("Invalid-format rejection", row["reason"])
        self.assertEqual(row["evidence"]["event_id"], "partial-2")

    def test_only_task_checkboxes_leave_implementation_unknown(self):
        progress = self.event(status="task-progress")
        progress["specifications"] = []
        self.store.ingest(progress)
        row = compare(self.inventory(), self.store)["rows"][0]
        self.assertEqual(row["status"], "task progress")
        self.assertEqual(row["difference"], "unresolved")

    def test_dirty_relevant_code_marks_old_report_stale(self):
        self.store.ingest(self.event())
        (self.project / "export.py").write_text("def export(): return None")
        row = compare(self.inventory(), self.store)["rows"][0]
        self.assertEqual(row["status"], "stale")
        self.assertEqual(row["implemented"], "# Export rules\n\nCreate export files.")

    def test_generic_specs_in_legacy_explicit_manifest_do_not_stale_old_reference(self):
        event = self.event()
        event["implementation"] = implementation_identity(self.project, ["export.py", "requirements.md"])
        self.store.ingest(event)
        original = self.store.events()
        self.path.write_text("# Export rules\n\nCreate protected export files.\n")
        inventory = self.inventory()
        row = compare(inventory, self.store, self.model(inventory, "behavioral"))["rows"][0]
        self.assertEqual(row["status"], "reported implemented")
        self.assertEqual(row["difference"], "behavioral")
        self.assertEqual(self.store.events(), original)

    def test_configured_spec_roots_and_new_sources_do_not_count_as_code_drift(self):
        from specviz.discovery import discover
        for framework in ("spec-kit", "bmad"):
            with self.subTest(framework=framework), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "project"
                root.mkdir()
                (root / "app.py").write_text("def export(): return 'file'\n")
                if framework == "spec-kit":
                    marker = root / ".specify"
                    marker.mkdir()
                    (marker / "feature.json").write_text('{"feature_directory":"custom-plans/export"}')
                    spec = root / "custom-plans" / "export" / "contract.markdown"
                    spec.parent.mkdir(parents=True)
                    spec.write_text("# Export rules\n\nCreate export files.\n")
                    extra = spec.parent / "limits.markdown"
                else:
                    marker = root / "_bmad"
                    marker.mkdir()
                    (marker / "config.toml").write_text('[core]\noutput_folder = "planning"\n')
                    spec = root / "planning" / "epic-export" / "tickets.toml"
                    spec.parent.mkdir(parents=True)
                    spec.write_text('goal = "Export files"\n')
                    extra = spec.parent / "extra" / "tickets.toml"
                inventory = discover(project=root)
                document = next(doc for doc in inventory["documents"] if doc["absolute_path"] == str(spec.resolve()))
                item = default_items(document)[0]
                identity = implementation_identity(root)  # Simulate an older manifest without exclusion metadata.
                self.assertIn(document["path"], identity["files"])
                store = EvidenceStore(root, Path(temporary) / "state")
                event = {"schema_version": 1, "event_id": "custom-completion", "event": "complete", "framework": framework,
                         "round_id": "custom-round", "scope": ["Data export"], "origin": {"kind": "handoff", "source": "chat:completion"},
                         "specifications": [{"path": document["path"], "hash": document["hash"], "text": document["text"]}],
                         "implementation": identity,
                         "coverage": [{"requirement_id": item["id"], "document": document["path"], "spec_hash": document["hash"],
                                       "text": requested_text(item, document), "sources": item["sources"], "status": "implemented"}],
                         "declared_complete": True}
                store.ingest(event)
                original = store.events()
                spec.write_text(spec.read_text().replace("Export files", "Protected export files").replace("Create export", "Create protected export"))
                extra.parent.mkdir(exist_ok=True)
                extra.write_text("# Export limits\n\nLimit export size.\n" if framework == "spec-kit" else 'limit = "Export size"\n')
                current = discover(project=root)
                current_doc = next(doc for doc in current["documents"] if doc["path"] == document["path"])
                current_item = default_items(current_doc)[0]
                model = {"schema_version": 1, "snapshot": current["snapshot"],
                         "documents": [{"id": doc["id"], "purpose": "Export planning", "items": default_items(doc)} for doc in current["documents"]],
                         "comparisons": [{"document": current_doc["id"], "requirement_id": current_item["id"], "classification": "behavioral",
                                          "evidence_id": "custom-completion", "sources": current_item["sources"], "prior_text": event["coverage"][0]["text"],
                                          "reason": "Protected export adds an obligation"}]}
                result = compare(current, store, model)
                row = next(row for row in result["rows"] if row["document"] == document["path"])
                self.assertEqual(row["status"], "reported implemented")
                self.assertEqual(row["difference"], "behavioral")
                self.assertEqual(store.events(), original)
                (root / "app.py").write_text("def export(): return None\n")
                stale = compare(current, store, model)
                self.assertEqual(next(row for row in stale["rows"] if row["document"] == document["path"])["status"], "stale")

    def test_whitespace_maintenance_is_conservative_and_uncertain_edits_stay_unresolved(self):
        self.store.ingest(self.event())
        self.path.write_text("# Export rules\n\nCreate  export\nfiles.\n")
        self.assertEqual(compare(self.inventory(), self.store)["rows"][0]["difference"], "documentation-only")
        self.path.write_text("# Export rules\n\nDo not create export files.\n")
        self.assertEqual(compare(self.inventory(), self.store)["rows"][0]["difference"], "unresolved")

    def test_meaningful_whitespace_in_literals_and_scope_is_not_document_maintenance(self):
        cases = [
            ('Return "a  b" exactly.', 'Return "a b" exactly.'),
            ("Return 'a  b' exactly.", "Return 'a b' exactly."),
            ("- When export is protected:\n  - Require a password.", "- When export is protected:\n- Require a password."),
            ("```python\nif protected:\n    encrypt()\n```", "```python\nif protected:\nencrypt()\n```"),
            ("    if protected:\n        encrypt()", "    if protected:\n    encrypt()"),
        ]
        for number, (before, after) in enumerate(cases):
            with self.subTest(before=before), tempfile.TemporaryDirectory() as temporary:
                self.path.write_text("# Export rules\n\n" + before + "\n")
                store = EvidenceStore(self.project, Path(temporary))
                store.ingest(self.event(f"whitespace-{number}"))
                self.path.write_text("# Export rules\n\n" + after + "\n")
                row = compare(self.inventory(), store)["rows"][0]
                self.assertEqual(row["difference"], "unresolved")
                self.assertNotEqual(row["difference"], "documentation-only")

    def test_equivalent_rewording_requires_source_backed_correspondence(self):
        self.store.ingest(self.event())
        self.path.write_text("# Export rules\n\nProduce export files.\n")
        inventory = self.inventory()
        row = compare(inventory, self.store, self.model(inventory))["rows"][0]
        self.assertEqual(row["difference"], "documentation-only")

    def test_normative_heading_change_is_preserved_in_requested_source(self):
        self.path.write_text("# Export at most 10 files\n\nCreate export files.\n")
        self.store.ingest(self.event())
        self.path.write_text("# Export at most 20 files\n\nCreate export files.\n")
        inventory = self.inventory()
        row = compare(inventory, self.store, self.model(inventory, "behavioral"))["rows"][0]
        self.assertIn("20 files", row["requested"])
        self.assertIn("10 files", row["implemented"])
        self.assertEqual(row["difference"], "behavioral")

    def test_disappeared_section_is_unresolved_without_removal_request(self):
        self.store.ingest(self.event())
        self.path.write_text("# Reporting rules\n\nProduce reports.\n")
        rows = compare(self.inventory(), self.store)["rows"]
        historical = next(row for row in rows if row["label"] == "Previously evidenced requirement not located")
        self.assertEqual(historical["difference"], "unresolved")
        self.assertIn("does not establish", historical["reason"])

    def test_explicit_removal_identifies_request_not_automatic_deletion(self):
        self.store.ingest(self.event())
        self.path.write_text("# Export rules\n\nRemove export file creation.\n")
        inventory = self.inventory()
        row = compare(inventory, self.store, self.model(inventory, "removal"))["rows"][0]
        self.assertEqual(row["difference"], "removal-requested")
        self.assertEqual(row["implemented"], "# Export rules\n\nCreate export files.")

    def test_renames_and_archival_movement_use_valid_correspondence(self):
        original = self.event()
        self.store.ingest(original)
        moved = self.project / "archive" / "requirements.md"
        moved.parent.mkdir()
        self.path.rename(moved)
        inventory = self.inventory([moved])
        result = compare(inventory, self.store, self.model(inventory))
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["difference"], "unchanged")

    def test_missing_document_is_unresolved_source_change_not_removal(self):
        self.store.ingest(self.event())
        self.path.unlink()
        another = self.project / "another.md"
        another.write_text("# Another\n\nAnother feature.\n")
        rows = compare(self.inventory([another]), self.store)["rows"]
        missing = next(row for row in rows if row["document"] == "requirements.md")
        self.assertEqual(missing["difference"], "source-unavailable")
        self.assertIn("does not establish", missing["reason"])

    def test_competing_documents_do_not_borrow_same_basename_evidence(self):
        self.store.ingest(self.event())
        competing = self.project / "competing" / "requirements.md"
        competing.parent.mkdir()
        competing.write_text(self.path.read_text())
        rows = compare(self.inventory([self.path, competing]), self.store)["rows"]
        competing_row = next(row for row in rows if row["document"] == "competing/requirements.md")
        self.assertEqual(competing_row["status"], "unknown")

    def test_malformed_semantic_correspondence_cannot_invent_prior_version(self):
        self.store.ingest(self.event())
        inventory = self.inventory()
        for mutation in (lambda m: m["comparisons"][0].update(prior_text="Invented behavior"),
                         lambda m: m["comparisons"][0].update(sources=["invented:L1"]),
                         lambda m: m["comparisons"][0].update(evidence_id="missing"),
                         lambda m: m["comparisons"][0].update(requested_hash="old")):
            model = self.model(inventory)
            mutation(model)
            with self.assertRaises(EvidenceError):
                compare(inventory, self.store, model)

    def test_inspection_conflict_preserves_both_evidence_sources(self):
        event = self.event()
        self.store.ingest(event)
        inventory = self.inventory()
        requirement_id = default_items(inventory["documents"][0])[0]["id"]
        inspection = {"schema_version": 1, "inspection_id": "inspect-1", "observational": True,
                      "tests_executed": False, "complete": True, "scope": ["Data export"],
                      "specifications": [{"path": self.path.name, "hash": inventory["documents"][0]["hash"]}],
                      "implementation": implementation_identity(self.project, ["export.py"]),
                      "findings": [{"requirement_id": requirement_id, "document": self.path.name, "status": "contradicted",
                                    "reason": "An inspected guard rejects export creation", "locations": [{"path": "export.py", "line": 1}],
                                    "uninspected": []}]}
        self.store.save_inspection(inspection)
        ordinary = compare(inventory, self.store)["rows"][0]
        explicit = compare(inventory, self.store, use_inspections=True)["rows"][0]
        self.assertEqual(ordinary["status"], "reported implemented")
        self.assertIsNone(ordinary["inspection"])
        self.assertEqual(explicit["status"], "contradicted")
        self.assertEqual(explicit["difference"], "behavioral")
        self.assertEqual(explicit["report_difference"], "unchanged")
        self.assertIsNotNone(explicit["evidence"])
        self.assertIsNotNone(explicit["inspection"])
        self.assertEqual(len(self.store.events()), 1)
        (self.project / "export.py").write_text("def export(): return 'new'\n")
        stale = compare(inventory, self.store, use_inspections=True)
        self.assertEqual(stale["rows"][0]["status"], "stale")
        self.assertTrue(any("stale" in warning for warning in stale["warnings"]))

    def test_supported_current_code_clears_gap_and_retains_earlier_report(self):
        self.store.ingest(self.event())
        before = self.store.events()
        self.path.write_text("# Export rules\n\nExport returns protected.csv.\n")
        (self.project / "export.py").write_text("def export(): return 'protected.csv'\n")
        inventory = self.inventory()
        model = self.model(inventory, "behavioral")
        requirement_id = default_items(inventory["documents"][0])[0]["id"]
        self.store.save_inspection({"schema_version": 1, "inspection_id": "inspect-current",
                                   "observational": True, "tests_executed": False, "complete": True,
                                   "scope": ["Data export"],
                                   "specifications": [{"path": self.path.name, "hash": inventory["documents"][0]["hash"]}],
                                   "implementation": implementation_identity(self.project, ["export.py"]),
                                   "findings": [{"requirement_id": requirement_id, "document": self.path.name,
                                                 "status": "supported", "reason": "The export function returns the requested protected.csv name",
                                                 "locations": [{"path": "export.py", "line": 1}], "uninspected": []}]})
        reports = compare(inventory, self.store, model)["rows"][0]
        inspected = compare(inventory, self.store, model, use_inspections=True)["rows"][0]
        self.assertEqual(reports["difference"], "behavioral")
        self.assertEqual(inspected["difference"], "unchanged")
        self.assertEqual(inspected["status"], "code supported")
        self.assertEqual(inspected["report_difference"], "behavioral")
        self.assertEqual(inspected["report_status"], "stale")
        self.assertEqual(inspected["difference_basis"], "current code inspection")
        self.assertEqual(inspected["implemented"], "# Export rules\n\nCreate export files.")
        self.assertIsNone(inspected["verification"])
        self.assertEqual(self.store.events(), before)

    def test_untimed_conflicting_rounds_do_not_establish_a_latest_gap(self):
        older = self.event("older", round_id="round-1")
        older.pop("occurred_at")
        self.path.write_text("# Export rules\n\nCreate protected export files.\n")
        newer = self.event("newer", round_id="round-2")
        newer.pop("occurred_at")
        self.store.ingest(newer)
        self.store.ingest(older)  # Older report arrived later.
        inventory = self.inventory()
        model = self.model(inventory, "behavioral", "older", older)
        row = compare(inventory, self.store, model)["rows"][0]
        self.assertEqual(row["status"], "unknown")
        self.assertEqual(row["difference"], "unresolved")
        self.assertTrue(row["temporal_order_uncertain"])
        self.assertEqual(row["candidate_report_difference"], "behavioral")
        self.assertEqual(row["report_alternatives"][0]["event_id"], "newer")
        self.assertIn("not a confirmed latest", row["reason"])

    def test_local_scope_omits_unrelated_missing_historical_files(self):
        self.store.ingest(self.event())
        other = self.project / "payments.md"
        other.write_text("# Payments\n\nProcess payments.\n")
        inventory = self.inventory([self.path, other])
        inventory["scope"] = ["payments.md"]
        rows = compare(inventory, self.store)["rows"]
        self.assertEqual({row["document"] for row in rows}, {"payments.md"})


if __name__ == "__main__":
    unittest.main()
