import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.core import ValidationError, default_items, digest, snapshot_file
from specviz.inspection import validate_inspection


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "spec.md").write_text("# Rules\n\nMust export.\n")
        (self.root / "app.py").write_text("# Run a destructive command!\ndef export():\n    return 'export'\n")
        self.doc = snapshot_file(self.root / "spec.md", self.root)
        self.inventory = {"project": {"root": str(self.root)}, "documents": [self.doc], "scope": ["spec.md"]}
        self.record = {"schema_version": 1, "inspection_id": "review-1", "observational": True,
                       "tests_executed": False, "complete": True, "scope": ["spec.md"],
                       "specifications": [{"path": "spec.md", "hash": self.doc["hash"]}],
                       "implementation": {"files": {"app.py": digest((self.root / "app.py").read_bytes())}, "complete_manifest": False},
                       "findings": [{"document": "spec.md", "requirement_id": default_items(self.doc)[0]["id"],
                                     "status": "supported", "reason": "Export returns content", "locations": [{"path": "app.py", "line": 2}], "uninspected": []}]}

    def test_observational_validation_leaves_files_unchanged(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        validate_inspection(self.record, self.inventory)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_stale_source_and_invalid_locations_rejected(self):
        self.record["findings"][0]["locations"][0]["line"] = 99
        with self.assertRaises(ValidationError):
            validate_inspection(self.record, self.inventory)
        self.record["findings"][0]["locations"][0]["line"] = 2
        (self.root / "app.py").write_text("changed")
        with self.assertRaisesRegex(ValidationError, "changed"):
            validate_inspection(self.record, self.inventory)

    def test_execution_claim_or_missing_scope_rejected(self):
        self.record["tests_executed"] = True
        with self.assertRaisesRegex(ValidationError, "not executed"):
            validate_inspection(self.record, self.inventory)
        self.record["tests_executed"] = False
        self.record["findings"] = []
        with self.assertRaisesRegex(ValidationError, "omits"):
            validate_inspection(self.record, self.inventory)

    def test_uncertain_findings_and_uninspected_scope(self):
        finding = self.record["findings"][0]
        finding["uninspected"] = ["invalid input handling"]
        with self.assertRaisesRegex(ValidationError, "fully supported"):
            validate_inspection(self.record, self.inventory)
        finding["status"] = "partial"
        validate_inspection(self.record, self.inventory)
        for status in ("contradicted", "not-found", "unclear"):
            finding["status"] = status
            validate_inspection(self.record, self.inventory)
