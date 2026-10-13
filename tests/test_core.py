import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.core import (ValidationError, default_items, digest, parse_blocks,
                         read_stable, snapshot_file, validate_inventory, validate_model)


class SourceTests(unittest.TestCase):
    def test_blocks_preserve_lists_tables_code_and_duplicate_headings(self):
        text = "# Export\n\n## Rules\n\n- Must finish within 30 seconds.\n  - Except encrypted exports.\n\n| Condition | Result |\n| --- | --- |\n| Invalid | Reject |\n\n```md\n# Not a heading\n```\n\n## Rules\n\nOptional download.\n\n<div>Unknown syntax</div>\n"
        blocks = parse_blocks(text, "spec.md")
        self.assertEqual([b["kind"] for b in blocks], ["heading", "heading", "list", "table", "code", "heading", "paragraph", "unknown"])
        covered = {line for b in blocks for line in range(b["start_line"], b["end_line"] + 1)}
        nonblank = {i for i, line in enumerate(text.splitlines(), 1) if line.strip()}
        self.assertTrue(nonblank <= covered)
        items = default_items({"id": "spec.md", "blocks": blocks})
        self.assertEqual(len({item["id"] for item in items}), len(items))
        self.assertIn("30 seconds", json.dumps(items))
        self.assertIn("Except encrypted", json.dumps(items))

    def test_snapshot_hashes_original_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "spec.md"
            file.write_bytes(b"# Test\r\n\r\nMust work.\r\n")
            doc = snapshot_file(file, root)
            self.assertEqual(doc["hash"], digest(file.read_bytes()))
            self.assertEqual(doc["path"], "spec.md")
            file.write_bytes(b"\xef\xbb\xbf# Test\r\n\r\nMust work.\r\n")
            doc = snapshot_file(file, root)
            self.assertEqual(digest(doc["text"]), doc["hash"])
            self.assertEqual(doc["title"], "Test")

    def test_record_versions_and_relationships_are_validated(self):
        record = {"schema_version": 1, "project": {"root": "/example"},
                  "documents": [{"id": "one", "path": "one", "hash": "hash", "text": "text", "blocks": []}],
                  "groups": [{"id": "group"}], "scope": ["one"], "context": [],
                  "relationships": [{"from": "group", "to": "one", "type": "containment"}]}
        validate_inventory(record)
        record["schema_version"] = 2
        with self.assertRaises(ValidationError):
            validate_inventory(record)
        record["schema_version"] = 1
        record["relationships"][0]["to"] = "invented"
        with self.assertRaises(ValidationError):
            validate_inventory(record)

    def test_independent_list_obligations_have_separate_source_spans(self):
        blocks = parse_blocks("# Rules\n\n- Protect files.\n  - Never log passwords.\n- Validate ownership.\n", "rules.md")
        self.assertEqual(blocks[1]["text"], "- Protect files.\n  - Never log passwords.")
        self.assertEqual(blocks[2]["text"], "- Validate ownership.")
        self.assertNotEqual(blocks[1]["id"], blocks[2]["id"])

    def test_concurrent_source_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "spec.md"
            file.write_text("one")
            original = Path.stat
            count = 0

            def changing(path, *args, **kwargs):
                nonlocal count
                count += 1
                if count % 2 == 0:
                    with file.open("a") as stream:
                        stream.write("x")
                return original(path, *args, **kwargs)

            with patch.object(Path, "stat", changing):
                with self.assertRaises(ValidationError):
                    read_stable(file)

    def test_model_requires_coverage_and_valid_source_snapshot(self):
        blocks = parse_blocks("# Export\n\nMust work.\n\nNever leak passwords.\n", "spec.md")
        doc = {"id": "spec.md", "blocks": blocks}
        inventory = {"snapshot": "snapshot-1", "documents": [doc], "scope": ["spec.md"]}
        model = {"schema_version": 1, "snapshot": "snapshot-1", "documents": [
            {"id": "spec.md", "purpose": "Export safely", "items": [
                {"id": "safe", "label": "Safe export", "sources": [blocks[1]["id"]], "notes": []}
            ], "unresolved": [blocks[2]["id"]]}
        ]}
        validate_model(model, inventory)
        model["documents"][0]["unresolved"] = []
        with self.assertRaisesRegex(ValidationError, "omits"):
            validate_model(model, inventory)
        model["documents"][0]["items"][0]["sources"] = ["invented"]
        with self.assertRaisesRegex(ValidationError, "invented"):
            validate_model(model, inventory)
        model["snapshot"] = "old"
        with self.assertRaisesRegex(ValidationError, "snapshot"):
            validate_model(model, inventory)


if __name__ == "__main__":
    unittest.main()
