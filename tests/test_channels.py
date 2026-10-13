"""Release selection must never silently enroll a stable user into beta."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path

from test_install import installer
from bundle import BundleError, RELEASE, seal, validate

ROOT = Path(__file__).resolve().parents[1]


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        home_patch = patch.object(installer.Path, "home", return_value=self.home)
        home_patch.start()
        self.addCleanup(home_patch.stop)
        self.project = self.root / "project"
        self.project.mkdir()
        self.stable = self.make_source("stable", "0.1.0")
        self.beta = self.make_source("beta", "0.2.0-beta.1")

    def make_source(self, channel, version):
        source = self.root / channel
        source.mkdir()
        (source / "SKILL.md").write_text(f"{channel} instructions", encoding="utf-8")
        (source / "scripts/specviz").mkdir(parents=True)
        (source / "scripts/specviz/__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
        if channel == "beta":
            (source / "scripts/specviz_bridge.py").write_text("# beta callback fixture\n")
            (source / "scripts/specviz/display.py").write_text("# beta display fixture\n")
        seal(source, channel, version)
        return source

    def test_default_install_and_update_remain_stable(self):
        result = installer.install(self.project, ["codex"], source=self.stable)
        self.assertEqual(result[0]["channel"], "stable")
        target = self.project / ".agents/skills/specviz"
        before = {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}
        with self.assertRaisesRegex(installer.InstallError, "Requested stable"):
            installer.install(self.project, ["codex", "claude-code"], source=self.beta)
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()})
        self.assertFalse((self.project / ".claude").exists())

    def test_explicit_beta_and_return_to_stable_keep_unrelated_data(self):
        installer.install(self.project, ["codex"], source=self.stable)
        target = self.project / ".agents/skills/specviz"
        (target / "reader-notes.md").write_text("keep", encoding="utf-8")
        evidence = self.root / "evidence.json"
        evidence.write_text('{"completion": "retained"}', encoding="utf-8")
        result = installer.install(self.project, ["antigravity"], source=self.beta, channel="beta")
        self.assertEqual(result[0]["channel"], "beta")
        installed = json.loads((target / installer.MANIFEST).read_text())
        self.assertEqual(installed["hosts"], ["antigravity", "codex"])
        self.assertEqual(installed["source_identity"], validate(self.beta, "beta")[0]["source_identity"])
        installer.install(self.project, ["codex"], source=self.stable)
        self.assertEqual((target / "reader-notes.md").read_text(), "keep")
        self.assertEqual(evidence.read_text(), '{"completion": "retained"}')
        self.assertEqual(json.loads((target / installer.MANIFEST).read_text())["channel"], "stable")

    def test_legacy_installation_is_stable(self):
        installer.install(self.project, ["codex"], source=self.stable)
        target = self.project / ".agents/skills/specviz"
        path = target / installer.MANIFEST
        manifest = json.loads(path.read_text())
        del manifest["channel"]
        del manifest["source_identity"]
        path.write_text(json.dumps(manifest))
        self.assertEqual(installer._owned(target)["channel"], "stable")
        installer.install(self.project, ["codex"], source=self.stable)
        self.assertEqual(json.loads(path.read_text())["channel"], "stable")

    def test_modified_or_relabelled_source_is_rejected_before_install(self):
        metadata = self.beta / RELEASE
        original = metadata.read_bytes()
        value = json.loads(original)
        value["channel"] = "stable"
        metadata.write_text(json.dumps(value))
        with self.assertRaises(installer.InstallError):
            installer.install(self.project, ["codex"], source=self.beta)
        metadata.write_bytes(original)
        (self.beta / "SKILL.md").write_text("unrecorded change")
        with self.assertRaisesRegex(installer.InstallError, "Release content"):
            installer.install(self.project, ["codex"], source=self.beta, channel="beta")
        self.assertEqual(list(self.project.iterdir()), [])

    def test_helper_version_and_metadata_must_agree(self):
        (self.stable / "scripts/specviz/__init__.py").write_text('__version__ = "0.2.0-beta.1"\n')
        seal(self.stable, "stable", "0.1.0")
        with self.assertRaisesRegex(BundleError, "helper version"):
            validate(self.stable)

    def test_uninstall_does_not_require_original_release_bundle(self):
        installer.install(self.project, ["codex"], source=self.stable)
        shutil.rmtree(self.stable)
        installer.install(self.project, ["codex"], source=self.stable, remove=True)
        self.assertFalse((self.project / ".agents/skills/specviz").exists())

    def test_current_package_is_reproducible_and_identified(self):
        release = json.loads((ROOT / "skills/specviz/release.json").read_text())
        paths = [self.root / "one.zip", self.root / "two.zip"]
        for output in paths:
            result = subprocess.run([sys.executable, str(ROOT / "tools/package.py"),
                                     "--channel", release["channel"], "--output", str(output)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
        record = json.loads(paths[0].with_suffix(".json").read_text())
        self.assertEqual(record["sha256"], hashlib.sha256(paths[0].read_bytes()).hexdigest())
        with zipfile.ZipFile(paths[0]) as archive:
            self.assertIn("LICENSE", archive.namelist())
            self.assertEqual(json.loads(archive.read("specviz/release.json")), release)

    @unittest.skipUnless(shutil.which("git"), "Git is needed to exercise checkout conversion")
    def test_windows_checkout_preserves_release_bytes_and_package(self):
        source, checkout = self.root / "source", self.root / "windows-checkout"
        source.mkdir()
        checkout.mkdir()
        for name in (".gitattributes", "LICENSE", "docs/installation.md"):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        for name in ("skills/specviz", "tools"):
            shutil.copytree(ROOT / name, source / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        for command in (
            ["git", "init", "--quiet"],
            ["git", "-c", "core.autocrlf=false", "add", "."],
            ["git", "-c", "core.autocrlf=true", "checkout-index", "--all",
             "--prefix=" + checkout.as_posix() + "/"],
        ):
            result = subprocess.run(command, cwd=source, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        release = json.loads((ROOT / "skills/specviz/release.json").read_text())
        for name, expected in release["files"].items():
            actual = hashlib.sha256((checkout / "skills/specviz" / name).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, f"Git checkout changed sealed bytes: {name}")
        packages = []
        for name, root in (("original", ROOT), ("windows", checkout)):
            output = self.root / (name + ".zip")
            result = subprocess.run([sys.executable, str(root / "tools/package.py"),
                                     "--channel", release["channel"], "--output", str(output)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            packages.append(output.read_bytes())
        self.assertEqual(packages[0], packages[1])


if __name__ == "__main__":
    unittest.main()
