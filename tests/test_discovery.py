"""Executable coverage for every supported layout and discovery boundary."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.core import validate_inventory
from specviz.discovery import DiscoveryError, discover, resolve_project, select_inventory


FIXTURES = Path(__file__).parent / "fixtures" / "frameworks"


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def write(self, path, text="# Document\n\nPurpose.\n"):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        return destination

    def fixture(self, name):
        shutil.copytree(FIXTURES / name / "project", self.root, dirs_exist_ok=True)
        return self.root

    def test_each_documented_framework_has_pinned_provenance_and_valid_inventory(self):
        for name in ("openspec", "spec-kit", "bmad", "superpowers", "kiro"):
            with self.subTest(framework=name):
                provenance = json.loads((FIXTURES / name / "provenance.json").read_text())
                self.assertTrue(provenance.get("commit") or provenance.get("version"))
                self.assertTrue(provenance["source_url"].startswith("https://"))
                inventory = discover(FIXTURES / name / "project")
                validate_inventory(inventory)
                self.assertTrue(inventory["documents"])
                self.assertEqual({d["framework"] for d in inventory["documents"]}, {name})
                self.assertTrue(all(g["layout"]["version"] == 1 for g in inventory["groups"]))
                self.assertEqual(inventory["scope"], [d["id"] for d in inventory["documents"]])
                self.assertTrue(all(d["implementation"] == "unknown" for d in inventory["documents"]))

    def test_project_from_subdirectory_and_explicit_override(self):
        self.fixture("openspec")
        nested = self.root / "openspec" / "changes" / "password-export"
        self.assertEqual(resolve_project(cwd=nested), self.root.resolve())
        inventory = discover(cwd=nested)
        self.assertTrue(any(d["path"].startswith("openspec/specs/") for d in inventory["documents"]))
        empty = self.root / "other"
        empty.mkdir()
        self.assertEqual(resolve_project(empty, nested), empty.resolve())
        with self.assertRaises(DiscoveryError):
            resolve_project(self.root / "missing")

    def test_cli_explicit_project_and_generic_scope_from_a_subdirectory(self):
        from specviz.cli import parser, run
        self.fixture("openspec")
        self.write("docs/design.md", "# Local design\n\n[Shared rules](../shared/rules.md)\n")
        self.write("shared/rules.md", "# Shared rules\n\nPreserve access checks.\n")
        nested = self.root / "openspec/changes/password-export"
        arguments = parser().parse_args(["show", "docs/design.md", "--project", str(self.root), "--json", "--state-dir", str(Path(self.temporary.name) / "state")])
        with patch("specviz.discovery.Path.cwd", return_value=nested):
            inventory = run(arguments)
        self.assertEqual(inventory["project"]["root"], str(self.root.resolve()))
        self.assertEqual(inventory["scope"], ["docs/design.md"])
        self.assertEqual(inventory["context"], ["shared/rules.md"])

    def test_explicit_subdirectory_is_respected_as_the_project(self):
        self.fixture("openspec")
        directory = self.root / "docs"
        self.write("docs/design.md")
        inventory = discover(project=directory, selections=["design.md"])
        self.assertEqual(inventory["project"]["root"], str(directory.resolve()))
        self.assertEqual([d["path"] for d in inventory["documents"]], ["design.md"])

    def test_mixed_frameworks_and_installed_skills_are_not_product_specs(self):
        for name in ("openspec", "spec-kit", "bmad", "superpowers", "kiro"):
            self.fixture(name)
        self.write(".agents/skills/foreign/SKILL.md")
        self.write("node_modules/library/spec.md")
        self.write("openspec/changes/password-export/.cache/cache.md")
        inventory = discover(self.root)
        self.assertEqual({d["framework"] for d in inventory["documents"]}, {"openspec", "spec-kit", "bmad", "superpowers", "kiro"})
        self.assertFalse(any("SKILL.md" in d["path"] or "cache.md" in d["path"] for d in inventory["documents"]))
        selected = discover(self.root, [".agents/skills/foreign/SKILL.md"])
        self.assertEqual(len(selected["scope"]), 1)
        self.assertEqual(next(d["framework"] for d in selected["documents"] if d["id"] in selected["scope"]), "generic")

    def test_openspec_branching_competing_changes_and_delta_lineage(self):
        self.fixture("openspec")
        self.write("openspec/changes/alternate-export/design.md")
        inventory = discover(self.root)
        proposal = "openspec/changes/password-export/proposal.md"
        design = "openspec/changes/password-export/design.md"
        specification = "openspec/changes/password-export/specs/data-export/spec.md"
        tasks = "openspec/changes/password-export/tasks.md"
        workflows = {(r["from"], r["to"]) for r in inventory["relationships"] if r["type"] == "workflow"}
        self.assertTrue({(proposal, design), (proposal, specification), (design, tasks), (specification, tasks)} <= workflows)
        self.assertNotIn((specification, design), workflows)
        self.assertEqual(len([g for g in inventory["groups"] if g["framework"] == "openspec" and g["lifecycle"] == "proposed"]), 2)
        archive = next(d for d in inventory["history"] if "archive" in d["path"])
        self.assertEqual(archive["lifecycle"], "archived")
        self.assertEqual(archive["change"], "add-export")
        lineage = next(d["lineage"] for d in inventory["documents"] if d["id"] == design)
        moved = self.root / "openspec/changes/archive/2026-10-12-password-export"
        shutil.move(self.root / "openspec/changes/password-export", moved)
        after = discover(self.root)
        self.assertEqual(next(d["lineage"] for d in after["history"] if d["path"].endswith("password-export/design.md")), lineage)
        self.assertTrue(all(d["implementation"] == "unknown" for d in after["documents"]))

    def test_openspec_unknown_schema_and_unavailable_declared_store(self):
        self.fixture("openspec")
        self.write("openspec/config.yaml", "schema: custom-flow\nreferences:\n  - team-plans\n")
        with patch("specviz.discovery.shutil.which", return_value=None):
            inventory = discover(self.root)
        self.assertTrue(any("store" in w and "unavailable" in w for w in inventory["warnings"]))
        self.assertTrue(any("custom-flow" in w for w in inventory["warnings"]))
        self.assertFalse(any(r["type"] == "workflow" for r in inventory["relationships"]))

    def test_openspec_local_root_has_precedence_over_store_declaration(self):
        self.fixture("openspec")
        self.write("openspec/config.yaml", "schema: spec-driven\nstore: team-plans\n")
        with patch("specviz.discovery.subprocess.run") as registry:
            inventory = discover(self.root)
        registry.assert_not_called()
        self.assertTrue(any("declaration ignored" in w for w in inventory["warnings"]))
        self.assertFalse(any(d["path"].startswith("external::") for d in inventory["documents"]))

    def test_openspec_registered_external_store_and_unknown_yaml_reference(self):
        self.write("openspec/config.yaml", "schema: spec-driven\nreferences:\n  - team-plans\n  - { id: unknown, remote: elsewhere }\n")
        external = Path(self.temporary.name) / "shared"
        document = external / "openspec/specs/data-export/spec.md"
        document.parent.mkdir(parents=True)
        document.write_text("# Shared rules\n\nShared export rules.\n")
        report = subprocess.CompletedProcess([], 0, json.dumps({"stores": [{"id": "team-plans", "root": str(external)}]}), "")
        with patch("specviz.discovery.shutil.which", return_value="openspec"), patch("specviz.discovery.subprocess.run", return_value=report):
            inventory = discover(self.root)
        self.assertTrue(any(d["path"].startswith("external::") for d in inventory["documents"]))
        self.assertTrue(any("Unsupported configuration syntax" in w for w in inventory["warnings"]))

    def test_spec_kit_configured_and_override_roots_do_not_reduce_global_scope(self):
        self.fixture("spec-kit")
        self.write("specs/002-payments/spec.md", "# Payments\n\nPayment requirements.\n")
        self.write("plans/custom/spec.md", "# Custom feature\n\nCustom requirements.\n")
        self.write(".specify/feature.json", '{"feature_directory":"plans/custom"}')
        external = Path(self.temporary.name) / "external-feature"
        external.mkdir()
        (external / "spec.md").write_text("# External feature\n\nExternal requirements.\n")
        with patch.dict(os.environ, {"SPECIFY_FEATURE_DIRECTORY": str(external)}):
            inventory = discover(self.root)
        specs = [d for d in inventory["documents"] if d["role"] == "specification"]
        self.assertEqual(len(specs), 4)
        self.assertTrue(any(d["path"].startswith("external::") for d in specs))
        with self.assertRaisesRegex(DiscoveryError, "Ambiguous"):
            select_inventory(inventory, ["spec.md"])
        self.assertTrue(any(d["role"] == "contract" for d in inventory["documents"]))

    def test_spec_kit_missing_optional_artifacts_and_missing_root(self):
        self.write(".specify/feature.json", '{"feature_directory":"missing"}')
        self.write("specs/001-export/spec.md")
        inventory = discover(self.root)
        self.assertEqual(len(inventory["documents"]), 1)
        self.assertTrue(any("feature root unavailable" in w for w in inventory["warnings"]))
        self.assertFalse(any(r["type"] == "workflow" for r in inventory["relationships"]))

    def test_bmad_toml_roots_ticket_collection_and_built_is_not_completion(self):
        self.fixture("bmad")
        self.write("planning/initiative-other/spec-another/spec-another.md")
        inventory = discover(self.root)
        plan = next(d for d in inventory["documents"] if d["role"] == "story plan")
        self.assertEqual(plan["reported_status"], "built")
        self.assertEqual(plan["implementation"], "unknown")
        self.assertTrue(any(d["path"].startswith("planning/initiative-other") for d in inventory["documents"]))
        ticket = next(d for d in inventory["documents"] if d["role"] == "tickets")
        self.assertIn("Review download errors", ticket["text"])
        self.assertFalse(any("story-review" in d["path"] for d in inventory["documents"]))
        self.write("_bmad/custom/config.toml", '[core]\noutput_folder = ["planning"]\n')
        malformed = discover(self.root)
        self.assertTrue(any("Unsupported BMAD output root" in w for w in malformed["warnings"]))

    def test_superpowers_explicit_alternate_and_missing_references(self):
        self.fixture("superpowers")
        alternate = "docs/agreed-designs/export.md"
        self.write(alternate, "# Agreed export design\n\nAn agreed alternative location.\n")
        self.write("docs/superpowers/plans/2026-10-03-custom-export.md", f"# Custom plan\n\nSpec: {alternate}\n\n[Missing](../../missing.md)\n")
        inventory = discover(self.root)
        design = next(d for d in inventory["documents"] if d["path"] == alternate)
        self.assertEqual(design["framework"], "superpowers")
        self.assertTrue(design["alternate_location"])
        self.assertTrue(any(r.get("unresolved") == "../../missing.md" and r["source"]["line"] == 5 for r in inventory["relationships"]))
        self.assertTrue(any(r["to"] == alternate and r["type"] == "reference" for r in inventory["relationships"]))

    def test_upstream_bold_spec_field_and_paths_with_spaces(self):
        self.fixture("superpowers")
        self.write("docs/agreed designs/export.md")
        self.write("docs/superpowers/plans/2026-10-03-custom.md", "# Custom plan\n\n**Spec:** `docs/agreed designs/export.md`\n")
        inventory = discover(self.root)
        self.assertTrue(any(d["path"] == "docs/agreed designs/export.md" and d["framework"] == "superpowers" for d in inventory["documents"]))
        self.assertTrue(any(r["type"] == "reference" and r["to"] == "docs/agreed designs/export.md" for r in inventory["relationships"]))

    def test_kiro_both_workflow_orders_and_incomplete_features(self):
        self.fixture("kiro")
        requirements = ".kiro/specs/data-export/requirements.md"
        design = ".kiro/specs/data-export/design.md"
        first = discover(self.root)
        self.assertTrue(any(r["from"] == requirements and r["to"] == design and r["type"] == "workflow" for r in first["relationships"]))
        self.write(".kiro/specs/data-export/.config.kiro", '{"workflowType":"design-first"}')
        self.write(".kiro/specs/repair-export/bugfix.md", "# Repair export\n\nFix exported row counts.\n")
        after = discover(self.root)
        self.assertTrue(any(r["from"] == design and r["to"] == requirements and r["type"] == "workflow" for r in after["relationships"]))
        self.assertTrue(any(d["role"] == "bug description" for d in after["documents"]))
        self.assertEqual(len(after["groups"]), 2)

    def test_malformed_native_metadata_is_reported_without_crashing(self):
        self.fixture("kiro")
        self.fixture("openspec")
        self.write(".kiro/specs/data-export/.config.kiro", '{"workflowType":[],"specId":{}}')
        self.write("openspec/config.yaml", "schema:\n  - custom\nstore:\n  - invalid\nreferences: invalid\n")
        inventory = discover(self.root)
        self.assertTrue(any("Unsupported Kiro" in w for w in inventory["warnings"]))
        self.assertEqual(len([w for w in inventory["warnings"] if "Unsupported OpenSpec configuration" in w]), 3)
        validate_inventory(inventory)

    def test_generic_reference_cycles_missing_links_and_local_context(self):
        self.write("docs/design.md", "# Design\n\n[Shared requirements](../shared/rules.md)\n\n[Missing](missing.md)\n")
        self.write("shared/rules.md", "# Rules\n\n[Design](../docs/design.md)\n")
        inventory = discover(self.root, ["docs", "shared"])
        local = select_inventory(inventory, ["docs"])
        self.assertEqual(local["scope"], ["docs/design.md"])
        self.assertEqual(local["context"], ["shared/rules.md"])
        edges = {(r["from"], r["to"]) for r in local["relationships"] if r["type"] == "reference"}
        self.assertTrue({("docs/design.md", "shared/rules.md"), ("shared/rules.md", "docs/design.md")} <= edges)
        self.assertTrue(any(r.get("unresolved") == "missing.md" for r in local["relationships"]))
        self.assertTrue(any("Generic document view" in w for w in local["warnings"]))

    def test_select_unknown_existing_file_and_follow_related_context(self):
        self.write("docs/design.md", "# Design\n\n[Shared rules](../shared/rules.md)\n")
        self.write("shared/rules.md", "# Rules\n\nDo not expose passwords.\n")
        inventory = select_inventory(discover(self.root), ["docs/design.md"])
        self.assertEqual(inventory["scope"], ["docs/design.md"])
        self.assertEqual(inventory["context"], ["shared/rules.md"])
        validate_inventory(inventory)

    def test_external_identity_can_be_selected_from_inventory(self):
        external = Path(self.temporary.name) / "external.md"
        external.write_text("# External\n\nExternal source.\n")
        inventory = discover(self.root, [external])
        selected = select_inventory(inventory, [inventory["scope"][0]])
        self.assertEqual(selected["scope"], inventory["scope"])

    def test_external_sources_update_inventory_hashes(self):
        external = Path(self.temporary.name) / "external-feature"
        external.mkdir()
        source = external / "spec.md"
        source.write_text("# Export\n\nLimit downloads to 100 rows.\n")
        self.write(".specify/feature.json", json.dumps({"feature_directory": str(external)}))
        before = discover(self.root)
        source.write_text("# Export\n\nLimit downloads to 200 rows.\n")
        after = discover(self.root)
        self.assertNotEqual(before["snapshot"], after["snapshot"])
        self.assertNotEqual(before["documents"][0]["hash"], after["documents"][0]["hash"])

    def test_empty_selection_missing_file_and_duplicate_source_headings(self):
        inventory = discover(self.root)
        self.assertEqual(inventory["documents"], [])
        self.assertTrue(any("empty" in w for w in inventory["warnings"]))
        with self.assertRaises(DiscoveryError):
            discover(self.root, ["missing.md"])
        self.write("notes.md", "# Notes\n\n## Rules\n\nFirst rule.\n\n## Rules\n\nSecond rule.\n")
        selected = discover(self.root, ["notes.md"])
        blocks = selected["documents"][0]["blocks"]
        repeated = [b for b in blocks if b["kind"] == "heading" and b["heading"][-1] == "Rules"]
        self.assertEqual(len({b["id"] for b in repeated}), 2)

    def test_external_symlink_is_not_followed_without_explicit_selection(self):
        self.fixture("openspec")
        external = Path(self.temporary.name) / "external.md"
        external.write_text("# External\n\nExternal requirements.\n")
        link = self.root / "openspec/specs/data-export/external.md"
        try:
            link.symlink_to(external)
        except OSError:
            self.skipTest("Symlink creation unavailable on this platform")
        inventory = discover(self.root)
        self.assertFalse(any(d["path"].startswith("external::") for d in inventory["documents"]))
        self.assertTrue(any("External symlink excluded" in w for w in inventory["warnings"]))
        selected = discover(self.root, [str(link)])
        self.assertEqual(len(selected["scope"]), 1)
        self.assertTrue(selected["scope"][0].startswith("external::"))

    def test_unreadable_source_and_fenced_links_are_not_silently_included(self):
        self.fixture("openspec")
        unreadable = self.root / "openspec/specs/data-export/unreadable.md"
        unreadable.write_bytes(b"\xff\xfe")
        self.write("openspec/specs/data-export/sample.md", "# Sample\n\n```md\n[Example link](absent.md)\n```\n")
        inventory = discover(self.root)
        self.assertTrue(any("unreadable" in w for w in inventory["warnings"]))
        self.assertFalse(any(r.get("unresolved") == "absent.md" for r in inventory["relationships"]))


if __name__ == "__main__":
    unittest.main()
