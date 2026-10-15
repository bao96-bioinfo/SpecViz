"""Resolve reviewed reminder examples against actual delivered source keys.

These checks validate the examples and selection contract, not agent wording
or live chat delivery. See docs/interpretation-review.md for response review.
"""

import re
import shlex
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/specviz/scripts"))
from specviz.cli import parser, run
from specviz.core import ValidationError
from specviz.discovery import discover, select_inventory
from specviz.layout import TextBlock
from specviz.session import ViewStore
from specviz.views import overview_view


def primary_keys(inventory):
    return [identity for block in overview_view(inventory, omit_hint=True).blocks
            if isinstance(block, TextBlock) and block.context.startswith("Files")
            for identity in block.documents]


class OverviewGuidanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.state = self.root / "state"

    def fixture(self, name):
        source = (ROOT / "tests/fixtures/large-project/project" if name == "large-project"
                  else ROOT / "tests/fixtures/frameworks" / name / "project")
        project = self.root / name
        shutil.copytree(source, project)
        return project

    def invoke(self, project, *args):
        return run(parser().parse_intermixed_args([
            *args, "--project", str(project), "--state-dir", str(self.state)]))

    def test_reviewed_framework_examples_select_the_first_displayed_primary_file(self):
        examples = {
            "openspec": "openspec/specs/data-export/spec.md",
            "spec-kit": ".specify/memory/constitution.md",
            "bmad": "planning/initiative-reporting/epic-data-export/spec-data-export/spec-data-export.md",
            "superpowers": "docs/superpowers/plans/2026-10-02-data-export.md",
            "kiro": ".kiro/specs/data-export/design.md",
            "large-project": "openspec/specs/data-preparation/spec.md",
        }
        for framework, target in examples.items():
            with self.subTest(framework=framework):
                project = self.fixture(framework)
                inventory = discover(project)
                self.assertEqual(primary_keys(inventory)[0], target)
                self.invoke(project, "overview", "--omit-overview-hint", "--max-lines", "2000", "--session", framework)
                self.assertIn(target, ViewStore(project, self.state).latest(framework)["visible"])
                for prefix in ("$specviz", "/specviz"):
                    command = shlex.split(f"{prefix} show {shlex.quote(target)} --detailed")
                    result = self.invoke(project, *command[1:], "--json")
                    self.assertEqual(result["scope"], [target])
                self.assertFalse(list(self.state.glob("*.sqlite3")))

    def test_local_target_excludes_context_and_checks_ambiguity_across_the_project(self):
        project = self.fixture("openspec")
        folder = "openspec/changes/password-export/specs"
        inventory = discover(project, [folder])
        target = folder + "/data-export/spec.md"
        self.assertEqual(primary_keys(inventory), [target])
        self.assertTrue(inventory["context"])
        self.assertTrue(set(inventory["context"]).isdisjoint(primary_keys(inventory)))
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            select_inventory(inventory, ["spec.md"])
        self.assertEqual(select_inventory(inventory, [target])["scope"], [target])
        with self.assertRaisesRegex(ValidationError, "show accepts files"):
            self.invoke(project, "show", folder, "--json")

    def test_quoted_long_and_external_paths_preserve_the_literal_file(self):
        project = self.fixture("kiro")
        folder = project / "notes" / ("long-component-description-" * 4)
        folder.mkdir(parents=True)
        source = folder / "customer's export (draft).md"
        source.write_text("# Export\n\nOnly the owner can download the report.\n", encoding="utf-8")
        inventory = discover(project, [str(folder)])
        target = primary_keys(inventory)[0]
        self.assertGreater(len(target), 80)
        command = "$specviz show " + shlex.quote(target)
        self.assertNotIn("\n", command)
        self.assertEqual(self.invoke(project, *shlex.split(command)[1:], "--json")["scope"], [target])
        external = self.root / "shared plans"
        external.mkdir()
        shutil.copy2(source, external / source.name)
        inventory = discover(project, [str(external)])
        target = primary_keys(inventory)[0]
        self.assertTrue(target.startswith("external::"))
        self.assertEqual(self.invoke(project, *shlex.split("show " + shlex.quote(target)), "--json")["scope"], [target])

    def test_history_is_eligible_only_in_an_explicit_historical_overview(self):
        project = self.fixture("large-project")
        current = discover(project)
        history = discover(project, ["openspec/changes/archive"])
        target = primary_keys(history)[0]
        self.assertIn("/archive/", target)
        self.assertNotIn(target, primary_keys(current))
        self.assertEqual(self.invoke(project, "show", target, "--json")["scope"], [target])
        self.assertEqual(primary_keys(discover(project)), primary_keys(current))
        for invalid in ("Node 1", "[directory/files]", "openspec/.../spec.md"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.invoke(project, "show", invalid, "--json")

    def test_numbers_need_complete_keys_current_sources_and_the_same_conversation(self):
        project = self.fixture("large-project")
        inventory = discover(project)
        target = primary_keys(inventory)[0]
        number = str(next(i for i, doc in enumerate(inventory["documents"], 1) if doc["id"] == target))
        output = self.invoke(project, "--omit-overview-hint", "--max-lines", "12", "--session", "reader")
        token = re.search(r"--continue-view ([a-f0-9]+)", output)[1]
        views = ViewStore(project, self.state)
        with self.assertRaisesRegex(ValidationError, "not been exposed"):
            self.invoke(project, "show", number, "--session", "reader", "--json")
        for page in range(2, len(views.load(token)["pages"]) + 1):
            self.invoke(project, "--continue-view", token, "--page", str(page), "--session", "reader")
        self.assertEqual(self.invoke(project, "show", number, "--session", "reader", "--json")["scope"], [target])
        with self.assertRaisesRegex(ValidationError, "No file map"):
            self.invoke(project, "show", number, "--session", "other-reader", "--json")
        with self.assertRaisesRegex(ValidationError, "conversation's --session"):
            self.invoke(project, "show", number, "--json")
        (project / target).write_text("# Revised rules\n\nKeep answers private.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "changed"):
            self.invoke(project, "show", number, "--session", "reader", "--json")
        self.assertEqual(self.invoke(project, "show", target, "--json")["scope"], [target])


if __name__ == "__main__":
    unittest.main()
