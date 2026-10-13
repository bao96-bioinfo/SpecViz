"""Setup tests use isolated homes; no test writes actual host configuration."""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import test_channels as channels
from test_install import installer
from adapters import MARKER, identity
from transaction import Transaction


class AdapterTests(channels.ChannelTests):
    # Reuse bundle fixtures, not ChannelTests' test cases.
    def registry(self, host, project=None):
        directory = self.home / ".specviz/adapters" / host
        if host == "claude-code":
            directory /= identity(project or self.project)
        return directory / "registry.json"

    def install(self, hosts, **kwargs):
        return installer.install(kwargs.pop("project", self.project), hosts, source=kwargs.pop("source", self.beta),
                                 channel=kwargs.pop("channel", "beta"), user_dir=self.home, **kwargs)

    def test_claude_composes_inherited_command_and_keeps_other_hooks(self):
        user_settings = self.home / ".claude/settings.json"
        user_settings.parent.mkdir()
        original = {"type": "command", "command": "my-footer --original", "padding": 2}
        user_settings.write_text(json.dumps({"statusLine": original}))
        local = self.project / ".claude/settings.local.json"
        local.parent.mkdir()
        custom = {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "my-hook"}]}]}, "theme": "dark"}
        local.write_text(json.dumps(custom))
        with patch("subprocess.run", side_effect=AssertionError("Setup must not execute user commands")):
            self.install(["claude-code"])
            self.install(["claude-code"])
        value = json.loads(local.read_text())
        self.assertEqual(value["statusLine"]["padding"], 2)
        self.assertEqual(value["statusLine"]["refreshInterval"], 1)
        self.assertEqual(len(value["hooks"]["SessionStart"]), 2)
        self.assertEqual(json.loads(self.registry("claude-code").read_text())["previous_status"], original)
        self.install(["claude-code"], source=self.stable, channel="stable")
        self.assertEqual(json.loads(local.read_text()), custom)
        self.assertEqual(json.loads(user_settings.read_text()), {"statusLine": original})

    def test_antigravity_global_dispatcher_and_multiple_projects(self):
        settings = self.home / ".gemini/antigravity-cli/settings.json"
        settings.parent.mkdir(parents=True)
        previous = {"type": "command", "command": "custom-status", "padding": 1, "stack_with_default": False}
        settings.write_text(json.dumps({"statusLine": previous, "other": 7}))
        second = self.root / "second project"
        second.mkdir()
        self.install(["antigravity", "codex"])
        self.install(["antigravity"], project=second)
        registry = json.loads(self.registry("antigravity").read_text())
        self.assertEqual(len(registry["projects"]), 2)
        self.assertNotIn(str(self.project), json.loads(settings.read_text())["statusLine"]["command"])
        self.install(["antigravity"], remove=True)
        manifest = json.loads((self.project / ".agents/skills/specviz/.specviz-install.json").read_text())
        self.assertEqual(manifest["hosts"], ["codex"])
        self.assertEqual(len(json.loads(self.registry("antigravity").read_text())["projects"]), 1)
        self.install(["antigravity"], project=second, source=self.stable, channel="stable")
        self.assertEqual(json.loads(settings.read_text()), {"statusLine": previous, "other": 7})
        self.assertFalse((second / ".agents/hooks.json").exists())

    def test_default_antigravity_line_is_stacked_and_other_hooks_retained(self):
        hooks = self.project / ".agents/hooks.json"
        hooks.parent.mkdir()
        hooks.write_text('{"custom": {"SessionStart": []}}')
        self.install(["antigravity"])
        settings = self.home / ".gemini/antigravity-cli/settings.json"
        self.assertTrue(json.loads(settings.read_text())["statusLine"]["stack_with_default"])
        self.install(["antigravity"], remove=True)
        self.assertFalse(settings.exists())
        self.assertEqual(json.loads(hooks.read_text()), {"custom": {"SessionStart": []}})

    def test_later_status_edits_survive_downgrade_but_beta_update_conflicts(self):
        self.install(["claude-code"])
        settings = self.project / ".claude/settings.local.json"
        value = json.loads(settings.read_text())
        value["statusLine"]["command"] = "new-user-command"
        value["statusLine"]["padding"] = 8
        settings.write_text(json.dumps(value))
        with self.assertRaisesRegex(installer.InstallError, "were edited"):
            self.install(["claude-code"])
        self.install(["claude-code"], source=self.stable, channel="stable")
        self.assertEqual(json.loads(settings.read_text()), {"statusLine": {"command": "new-user-command", "padding": 8}})

    def test_configuration_conflict_preflights_all_skill_destinations(self):
        settings = self.project / ".agents/hooks.json"
        settings.parent.mkdir()
        settings.write_text(json.dumps({MARKER: {"SessionStart": [{"command": "mine"}]}}))
        with self.assertRaisesRegex(installer.InstallError, "conflicts"):
            self.install(["claude-code", "antigravity"])
        self.assertFalse((self.project / ".claude/skills/specviz/SKILL.md").exists())
        self.assertFalse((self.project / ".agents/skills/specviz/SKILL.md").exists())
        self.assertFalse((self.project / ".claude/settings.local.json").exists())

    def test_interruption_rolls_back_every_destination_and_settings(self):
        self.install(["claude-code", "antigravity"])
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*")
                  if p.is_file() and ".specviz-stage-" not in str(p)}
        replace = os.replace
        calls = 0

        def interrupt(source, target):
            nonlocal calls
            if ".specviz-stage-" in str(source):
                calls += 1
                if calls == 3:
                    raise KeyboardInterrupt()
            return replace(source, target)

        with patch("os.replace", side_effect=interrupt), self.assertRaises(KeyboardInterrupt):
            self.install(["claude-code", "antigravity"], source=self.stable, channel="stable")
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_next_install_recovers_process_interrupted_between_replacements(self):
        directory = self.home / ".specviz/adapters"
        directory.mkdir(parents=True)
        target = self.root / "owned.txt"
        backup = self.root / ".specviz-backup-test"
        stage = self.root / ".specviz-stage-test"
        backup.write_text("original")
        target.write_text("interrupted replacement")
        (directory / "install-transaction.json").write_text(json.dumps({"committed": False, "operations": [
            {"target": str(target), "backup": str(backup), "stage": str(stage), "existed": True}]}))
        with Transaction(directory):
            self.assertEqual(target.read_text(), "original")
        self.assertFalse(backup.exists())

    def test_stable_uninstaller_can_remove_one_shared_beta_registration(self):
        self.install(["antigravity", "codex"])
        self.install(["codex"], source=self.stable, channel="stable", remove=True)
        target = self.project / ".agents/skills/specviz"
        self.assertEqual(json.loads((target / installer.MANIFEST).read_text())["hosts"], ["antigravity"])
        self.assertEqual(len(json.loads(self.registry("antigravity").read_text())["projects"]), 1)

    def test_recursive_unowned_status_wrapper_is_rejected(self):
        settings = self.project / ".claude/settings.local.json"
        settings.parent.mkdir()
        settings.write_text('{"statusLine":{"command":"python specviz_bridge.py status"}}')
        with self.assertRaisesRegex(installer.InstallError, "recursive"):
            self.install(["claude-code"])


# Do not duplicate inherited channel checks in this suite.
for _name in tuple(vars(channels.ChannelTests)):
    if _name.startswith("test_"):
        setattr(AdapterTests, _name, None)


if __name__ == "__main__":
    unittest.main()
