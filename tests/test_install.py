import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("specviz_installer", ROOT / "tools/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        home_patch = patch.object(installer.Path, "home", return_value=self.home)
        home_patch.start()
        self.addCleanup(home_patch.stop)
        self.source = self.root / "bundle"
        self.source.mkdir()
        (self.source / "SKILL.md").write_text("Skill v1")
        (self.source / "scripts").mkdir()
        (self.source / "scripts/helper.py").write_text("print('helper')")
        from bundle import seal
        seal(self.source, "stable", "0.1.0")
        self.project = self.root / "project"
        self.project.mkdir()

    def test_shared_hosts_deduplicate_and_updates_removal_preserve_others(self):
        unrelated = self.project / ".agents/skills/other/SKILL.md"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("Other skill")
        result = installer.install(self.project, list(installer.HOSTS), source=self.source)
        self.assertEqual(len(result), 2)
        target = self.project / ".agents/skills/specviz"
        (target / "reader-notes.txt").write_text("Keep me")
        (self.source / "SKILL.md").write_text("Skill v2")
        from bundle import seal
        seal(self.source, "stable", "0.1.0")
        installer.install(self.project, list(installer.HOSTS), source=self.source, generation_handoff=True)
        self.assertEqual((target / "SKILL.md").read_text(), "Skill v2")
        self.assertTrue(json.loads((target / installer.MANIFEST).read_text())["generation_handoff"])
        installer.install(self.project, list(installer.HOSTS), source=self.source, remove=True)
        self.assertEqual((target / "reader-notes.txt").read_text(), "Keep me")
        self.assertEqual(unrelated.read_text(), "Other skill")

    def test_modified_owned_files_and_foreign_skills_refuse_all_changes(self):
        installer.install(self.project, ["codex"], source=self.source)
        target = self.project / ".agents/skills/specviz"
        (target / "SKILL.md").write_text("User's edit")
        with self.assertRaises(installer.InstallError):
            installer.install(self.project, ["codex", "claude-code"], source=self.source)
        self.assertFalse((self.project / ".claude/skills/specviz").exists())
        with self.assertRaises(installer.InstallError):
            installer.install(self.project, ["codex"], source=self.source, remove=True)

    def test_prerequisite_and_link_escape(self):
        with patch.object(sys, "version_info", (3, 10)):
            with self.assertRaises(installer.InstallError):
                installer.install(self.project, ["codex"], source=self.source)
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.project / ".agents").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable on this platform")
        with self.assertRaises(installer.InstallError):
            installer.install(self.project, ["codex"], source=self.source)


if __name__ == "__main__":
    unittest.main()
