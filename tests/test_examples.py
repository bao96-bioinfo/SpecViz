"""All advertised examples stay source-backed and reproduce their expected text."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.core import validate_model
from specviz.discovery import discover
from specviz.render import display_width, render_overview, render_show


REPOSITORY = Path(__file__).resolve().parents[1]
FRAMEWORKS = ("openspec", "spec-kit", "bmad", "superpowers", "kiro")


class FrameworkExampleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture_hashes = json.loads(
            (REPOSITORY / "tests/fixtures/frameworks/content-hashes.json").read_text(encoding="utf-8")
        )

    def test_all_five_examples_reproduce_source_backed_views(self):
        for framework in FRAMEWORKS:
            with self.subTest(framework=framework):
                source = REPOSITORY / "tests" / "fixtures" / "frameworks" / framework / "project"
                fixture = Path(self.temporary.name) / framework
                shutil.copytree(source, fixture)
                actual_hashes = {
                    path.relative_to(fixture).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(fixture.rglob("*")) if path.is_file()
                }
                self.assertEqual(self.fixture_hashes[framework], actual_hashes,
                                 "Fixture content changed; review interpretations and expected diagrams before updating hashes")
                example = REPOSITORY / "examples" / framework
                inventory = discover(fixture)
                model = json.loads((example / "model.json").read_text(encoding="utf-8"))
                # Snapshots include checkout-specific group identities. Rebind
                # only after checking every reviewed source and configuration.
                recorded_snapshot = model["snapshot"]
                model["snapshot"] = inventory["snapshot"]
                selection = json.loads((example / "selection.json").read_text(encoding="utf-8"))
                validate_model(model, inventory)
                documents = {document["id"]: document for document in inventory["documents"]}
                self.assertTrue(set(selection["files"]) <= set(documents))
                self.assertIn("Reporting service", (example / "README.md").read_text(encoding="utf-8"))
                for detailed in (False, True):
                    suffix = "-detailed" if detailed else ""
                    outputs = {
                        f"overview{suffix}.txt": render_overview(inventory, model, detailed=detailed),
                        f"show{suffix}.txt": render_show(inventory, selection["files"], model, detailed=detailed),
                    }
                    for filename, output in outputs.items():
                        with self.subTest(filename=filename):
                            expected = (example / filename).read_text(encoding="utf-8")
                            caption = f"Source snapshot:\n{recorded_snapshot}\n"
                            self.assertIn(caption, expected)
                            expected = expected.replace(caption, f"Source snapshot:\n{inventory['snapshot']}\n", 1)
                            self.assertEqual(output, expected)
                            self.assertTrue(all(display_width(line) <= 80 for line in output.splitlines()))
                            self.assertIn("Purpose:", output)
                            self.assertNotIn("[unresolved]", output)
                concise = (example / "show.txt").read_text(encoding="utf-8")
                detailed = (example / "show-detailed.txt").read_text(encoding="utf-8")
                for document in model["documents"]:
                    if document["id"] in selection["files"]:
                        for item in document["items"]:
                            label = item["label"]
                            self.assertIn(label, " ".join(concise.split()))
                            self.assertIn(label, " ".join(detailed.split()))
                self.assertIn("100 rows", " ".join(detailed.replace("|", " ").split()))


if __name__ == "__main__":
    unittest.main()
