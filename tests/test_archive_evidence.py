"""Hidden history remains provenance without becoming current work."""

import copy
import tempfile
import unittest
from pathlib import Path

from large_project_fixture import REPOSITORY
from specviz.comparison import compare, requested_text
from specviz.core import default_items, snapshot_file
from specviz.discovery import discover, specification_paths
from specviz.evidence import EvidenceStore, implementation_identity


class ArchiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.store = EvidenceStore(self.root, Path(self.temp.name) / "state")
        self.write("app.py", "result = 1\n")
        self.active = self.write(
            "openspec/changes/add-export/specs/export/spec.md",
            "# Export\n\nCreate files.\n",
        )
        self.current = self.write(
            "openspec/specs/export/spec.md", "# Export\n\nCreate files.\n"
        )

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def event(self, path):
        d = snapshot_file(path, self.root)
        item = default_items(d)[0]
        return {
            "schema_version": 1,
            "event": "complete",
            "event_id": "complete",
            "round_id": "round",
            "framework": "openspec",
            "scope": ["export"],
            "origin": {"kind": "handoff", "source": "reviewed completion report"},
            "declared_complete": True,
            "specifications": [
                {"path": d["path"], "hash": d["hash"], "text": d["text"]}
            ],
            "implementation": implementation_identity(self.root, ["app.py", d["path"]]),
            "coverage": [
                {
                    "requirement_id": item["id"],
                    "document": d["path"],
                    "spec_hash": d["hash"],
                    "text": requested_text(item, d),
                    "sources": item["sources"],
                    "status": "implemented",
                }
            ],
        }

    def archive(self):
        target = (
            self.root
            / "openspec/changes/archive/2026-01-01-add-export/specs/export/spec.md"
        )
        target.parent.mkdir(parents=True)
        self.active.rename(target)
        return target

    def test_verified_move_is_history_but_unexpected_deletion_and_ambiguity_are_unknown(
        self,
    ):
        self.store.ingest(self.event(self.active))
        before = self.store.events()
        archived = self.archive()
        rows = compare(discover(self.root), self.store)["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "unknown")
        duplicate = self.write(
            "openspec/changes/archive/2026-02-01-add-export/specs/export/spec.md",
            archived.read_text(),
        )
        rows = compare(discover(self.root), self.store)["rows"]
        self.assertTrue(any(r["difference"] == "source-unavailable" for r in rows))
        duplicate.unlink()
        archived.write_text("# Export\n\nDifferent behavior.\n")
        self.assertTrue(
            any(
                r["difference"] == "source-unavailable"
                for r in compare(discover(self.root), self.store)["rows"]
            )
        )
        archived.unlink()
        self.assertTrue(
            any(
                r["difference"] == "source-unavailable"
                for r in compare(discover(self.root), self.store)["rows"]
            )
        )
        self.assertEqual(self.store.events(), before)

    def test_known_archived_report_maps_only_through_explicit_valid_correspondence(
        self,
    ):
        archive = self.archive()
        event = self.event(archive)
        self.store.ingest(event)
        before = self.store.events()
        inventory = discover(self.root)
        doc = inventory["documents"][0]
        item = default_items(doc)[0]
        unknown = compare(inventory, self.store)["rows"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0]["status"], "unknown")
        model = {
            "schema_version": 1,
            "snapshot": inventory["snapshot"],
            "documents": [
                {
                    "id": doc["id"],
                    "purpose": "Export files",
                    "items": default_items(doc),
                }
            ],
            "comparisons": [
                {
                    "document": doc["id"],
                    "requirement_id": item["id"],
                    "classification": "equivalent",
                    "evidence_id": "complete",
                    "evidence_document": event["coverage"][0]["document"],
                    "evidence_requirement_id": event["coverage"][0]["requirement_id"],
                    "sources": item["sources"],
                    "prior_text": event["coverage"][0]["text"],
                    "reason": "The retained requirement and the current rule both require creating files.",
                }
            ],
        }
        for _ in range(2):
            row = compare(inventory, self.store, model)["rows"][0]
            self.assertEqual(row["status"], "reported implemented")
            self.assertIsNone(row["verification"])
        archive.write_text("# History\n\nAdditional historical annotation.\n")
        row = compare(discover(self.root), self.store, model)["rows"][0]
        self.assertEqual(row["status"], "reported implemented")
        self.write("app.py", "result = 2\n")
        self.assertEqual(
            compare(discover(self.root), self.store, model)["rows"][0]["status"],
            "stale",
        )
        self.assertEqual(self.store.events(), before)
        self.assertIn(
            archive.relative_to(self.root).as_posix(), specification_paths(inventory)
        )
