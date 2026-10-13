import json
import shutil
import tempfile
import unittest
from pathlib import Path

from diagram_fixture import REPOSITORY, load_fixture


class DiagramFixtureTests(unittest.TestCase):
    def test_eight_files_have_reviewed_sources_and_a_branch_and_join(self):
        inventory, model = load_fixture()
        self.assertEqual(len(inventory["documents"]), 8)
        self.assertEqual(sum(doc["path"].endswith("/spec.md") for doc in inventory["documents"]), 5)
        graph = model["project_view"]
        self.assertEqual(len([edge for edge in graph["relationships"] if edge["from"] == "prepare"]), 2)
        self.assertEqual(len([edge for edge in graph["relationships"] if edge["to"] == "evaluate"]), 2)
        covered = {ref["document"] for node in graph["nodes"] for ref in node["sources"]}
        self.assertEqual(covered, set(inventory["scope"]))
        self.assertIn("threshold is still undecided", graph["nodes"][4]["summary"])

    def test_maintained_diagram_views_reproduce_reviewed_model(self):
        from specviz.render import render_overview, render_show
        inventory, model = load_fixture()
        example = REPOSITORY / "examples/diagram-first"
        selection = json.loads((example / "selection.json").read_text())["files"]
        for detailed in (False, True):
            suffix = "-detailed" if detailed else ""
            for name, output in (("overview", render_overview(inventory, model, detailed)),
                                 ("show", render_show(inventory, selection, model, detailed))):
                expected = (example / f"{name}{suffix}.txt").read_text()
                recorded = json.loads((example / "model.json").read_text())["snapshot"]
                expected = expected.replace(recorded, inventory["snapshot"])
                self.assertEqual(output, expected)

    def test_copied_fixture_requires_exact_source_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "workspace"
            shutil.copytree(REPOSITORY / "tests/fixtures/diagram-first/project", project)
            inventory, _ = load_fixture(project)
            self.assertEqual(len(inventory["documents"]), 8)
            (project / "README.md").write_text("Changed purpose", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "review"):
                load_fixture(project)


if __name__ == "__main__":
    unittest.main()
