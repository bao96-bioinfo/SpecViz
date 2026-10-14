"""Current-work discovery, historical provenance, and saved selections."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from large_project_fixture import REPOSITORY, load_fixture
from specviz.core import ValidationError, validate_inventory
from specviz.discovery import discover
from specviz.session import ViewStore


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        shutil.copytree(REPOSITORY / "tests/fixtures/large-project/project", self.root)
        self.archive = self.root / "openspec/changes/archive"

    def tearDown(self):
        self.temp.cleanup()

    def test_current_and_broad_local_scope_have_ten_sources_and_no_history_keys(self):
        from specviz.views import overview_view

        for selections in (None, ["openspec/"]):
            inventory = discover(self.root, selections)
            validate_inventory(inventory)
            self.assertEqual(len(inventory["documents"]), 10)
            self.assertEqual(len(inventory["scope"]), 10)
            self.assertEqual(len(inventory["history"]), 8)
            self.assertTrue(
                all("text" not in h and "hash" not in h for h in inventory["history"])
            )
            self.assertTrue(
                all(g["lifecycle"] != "archived" for g in inventory["groups"])
            )
            self.assertNotIn("archive/", overview_view(inventory).render())
        inventory, model = load_fixture(self.root)
        self.assertEqual(len(model["project_view"]["nodes"]), 7)
        self.assertEqual(len(model["project_view"]["relationships"]), 8)

    def test_linked_archives_stay_excluded_but_explicit_history_retains_identity(self):
        path = self.root / "openspec/changes/add-notebook/design.md"
        path.write_text(
            path.read_text()
            + "\n[Earlier design](../archive/2026-01-01-initial-model/design.md)\n"
        )
        current = discover(self.root)
        self.assertEqual(len(current["documents"]), 10)
        self.assertFalse(any("Unresolved reference" in w for w in current["warnings"]))
        historical = discover(
            self.root, ["openspec/changes/archive/2026-01-01-initial-model/design.md"]
        )
        document = next(
            d for d in historical["documents"] if d["id"] in historical["scope"]
        )
        self.assertEqual(document["lifecycle"], "archived")
        self.assertEqual(document["framework"], "openspec")
        self.assertIn("change/initial-model/design.md", document["lineage"])
        self.assertEqual(len(discover(self.root)["documents"]), 10)

    def test_archive_only_is_empty_and_active_archive_named_change_is_current(self):
        shutil.rmtree(self.root / "openspec/specs")
        shutil.rmtree(self.root / "openspec/changes/add-notebook")
        for selections in (None, ["openspec/"]):
            inventory = discover(self.root, selections)
            self.assertEqual(inventory["documents"], [])
            self.assertEqual(inventory["groups"], [])
        path = self.root / "openspec/changes/improve-archive-search/proposal.md"
        path.parent.mkdir()
        path.write_text("# Search\n\nImprove historical search.\n")
        self.assertEqual(len(discover(self.root)["documents"]), 1)
        self.assertEqual(
            len(discover(self.root, ["openspec/changes/archive"])["scope"]), 8
        )

    def test_adapter_declared_history_cannot_return_as_generic_context(self):
        from specviz.discovery import ADAPTERS

        path = self.root / "old-plans/rule.md"
        path.parent.mkdir()
        path.write_text("# Old rule\n\nHistorical only.\n")
        source = self.root / "openspec/specs/evaluation/spec.md"
        source.write_text(
            source.read_text() + "\n[Old rule](../../../old-plans/rule.md)\n"
        )

        def adapter(builder):
            group = builder.group("custom", "old", "Historical rules", "archived")
            builder.add(path, "custom", group, "rule", "archived")

        with patch.dict(ADAPTERS, {"custom": adapter}):
            inventory = discover(self.root)
            explicit = discover(self.root, [path])
        self.assertNotIn("old-plans/rule.md", inventory["scope"])
        self.assertEqual(len(inventory["documents"]), 10)
        self.assertFalse(
            any("Unresolved reference" in w for w in inventory["warnings"])
        )
        self.assertIn("old-plans/rule.md", explicit["scope"])

    def test_external_store_obeys_the_same_policy(self):
        other = Path(self.temp.name) / "consumer"
        (other / "openspec").mkdir(parents=True)
        (other / "openspec/config.yaml").write_text(
            "schema: spec-driven\nreferences:\n  - shared\n"
        )
        response = subprocess.CompletedProcess(
            [],
            0,
            json.dumps({"stores": [{"id": "shared", "root": str(self.root)}]}),
            "",
        )
        with (
            patch("specviz.discovery.shutil.which", return_value="openspec"),
            patch("specviz.discovery.subprocess.run", return_value=response),
        ):
            current = discover(other)
            history = discover(other, [self.archive])
        self.assertEqual(len(current["documents"]), 10)
        self.assertTrue(
            all(d["path"].startswith("external::") for d in current["documents"])
        )
        self.assertEqual(len(current["history"]), 8)
        self.assertEqual(len(history["scope"]), 8)
        self.assertTrue(
            all(
                d["lifecycle"] == "archived"
                for d in history["documents"]
                if d["id"] in history["scope"]
            )
        )

    def test_archive_edits_do_not_stale_current_views_but_moves_refresh_selection(self):
        inventory = discover(self.root)
        store = ViewStore(self.root, Path(self.temp.name) / "state")
        token = store.save(inventory, ["current view"], "chat")
        historic = discover(self.root, [self.archive])
        history_token = store.save(historic, ["historical view"])
        next(self.archive.rglob("design.md")).write_text(
            "# Changed history\n\nHistorical note.\n"
        )
        self.assertEqual(discover(self.root)["snapshot"], inventory["snapshot"])
        self.assertEqual(store.load(token)["pages"], ["current view"])
        with self.assertRaisesRegex(ValidationError, "changed"):
            store.load(history_token)
        shutil.move(
            self.root / "openspec/changes/add-notebook",
            self.archive / "2026-02-01-add-notebook",
        )
        with self.assertRaisesRegex(ValidationError, "moved"):
            store.select(["1"], "chat")
        self.assertEqual(len(discover(self.root)["documents"]), 5)
