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
from legacy_beta import seed


class AdapterTests(channels.ChannelTests):
    # Reuse bundle fixtures, not ChannelTests' test cases.
    def registry(self, host, project=None):
        directory = self.home / ".specviz/adapters" / host
        if host == "claude-code":
            directory /= identity(project or self.project)
        return directory / "registry.json"

    def install(self, hosts, **kwargs):
        project = kwargs.pop("project", self.project)
        source = kwargs.pop("source", self.stable)
        channel = kwargs.pop("channel", "stable")
        return installer.install(
            project, hosts, source=source, channel=channel, user_dir=self.home, **kwargs
        )

    def seed(self, hosts, project=None):
        seed(project or self.project, self.home, hosts, self.beta)

    def test_claude_composes_inherited_command_and_keeps_other_hooks(self):
        user_settings = self.home / ".claude/settings.json"
        user_settings.parent.mkdir()
        original = {"type": "command", "command": "my-footer --original", "padding": 2}
        user_settings.write_text(json.dumps({"statusLine": original}))
        local = self.project / ".claude/settings.local.json"
        local.parent.mkdir()
        custom = {
            "hooks": {
                "SessionStart": [{"hooks": [{"type": "command", "command": "my-hook"}]}]
            },
            "theme": "dark",
        }
        local.write_text(json.dumps(custom))
        with patch(
            "subprocess.run",
            side_effect=AssertionError("Setup must not execute user commands"),
        ):
            self.seed(["claude-code"])
        value = json.loads(local.read_text())
        self.assertEqual(value["statusLine"]["padding"], 2)
        self.assertEqual(value["statusLine"]["refreshInterval"], 1)
        self.assertEqual(len(value["hooks"]["SessionStart"]), 2)
        self.assertEqual(
            json.loads(self.registry("claude-code").read_text())["previous_status"],
            original,
        )
        self.install(["claude-code"], source=self.stable, channel="stable")
        self.assertEqual(json.loads(local.read_text()), custom)
        self.assertEqual(
            json.loads(user_settings.read_text()), {"statusLine": original}
        )

    def test_antigravity_global_dispatcher_and_multiple_projects(self):
        settings = self.home / ".gemini/antigravity-cli/settings.json"
        settings.parent.mkdir(parents=True)
        previous = {
            "type": "command",
            "command": "custom-status",
            "padding": 1,
            "stack_with_default": False,
        }
        settings.write_text(json.dumps({"statusLine": previous, "other": 7}))
        second = self.root / "second project"
        second.mkdir()
        self.seed(["antigravity", "codex"])
        self.seed(["antigravity"], project=second)
        registry = json.loads(self.registry("antigravity").read_text())
        self.assertEqual(len(registry["projects"]), 2)
        self.assertNotIn(
            str(self.project), json.loads(settings.read_text())["statusLine"]["command"]
        )
        self.install(["antigravity"], remove=True)
        manifest = json.loads(
            (self.project / ".agents/skills/specviz/.specviz-install.json").read_text()
        )
        self.assertEqual(manifest["hosts"], ["codex"])
        self.assertEqual(
            len(json.loads(self.registry("antigravity").read_text())["projects"]), 1
        )
        self.install(
            ["antigravity"], project=second, source=self.stable, channel="stable"
        )
        self.assertEqual(
            json.loads(settings.read_text()), {"statusLine": previous, "other": 7}
        )
        self.assertFalse((second / ".agents/hooks.json").exists())

    def test_default_antigravity_line_is_stacked_and_other_hooks_retained(self):
        hooks = self.project / ".agents/hooks.json"
        hooks.parent.mkdir()
        hooks.write_text('{"custom": {"SessionStart": []}}')
        self.seed(["antigravity"])
        settings = self.home / ".gemini/antigravity-cli/settings.json"
        self.assertTrue(
            json.loads(settings.read_text())["statusLine"]["stack_with_default"]
        )
        self.install(["antigravity"], remove=True)
        self.assertFalse(settings.exists())
        self.assertEqual(
            json.loads(hooks.read_text()), {"custom": {"SessionStart": []}}
        )

    def test_later_status_edits_survive_downgrade_but_beta_update_conflicts(self):
        self.seed(["claude-code"])
        settings = self.project / ".claude/settings.local.json"
        value = json.loads(settings.read_text())
        value["statusLine"]["command"] = "new-user-command"
        value["statusLine"]["padding"] = 8
        settings.write_text(json.dumps(value))
        with self.assertRaisesRegex(installer.InstallError, "retired"):
            self.install(["claude-code"], channel="beta")
        self.install(["claude-code"], source=self.stable, channel="stable")
        self.assertEqual(
            json.loads(settings.read_text()),
            {"statusLine": {"command": "new-user-command", "padding": 8}},
        )

    def test_configuration_conflict_preflights_all_skill_destinations(self):
        self.seed(["claude-code", "antigravity"])
        settings = self.project / ".agents/hooks.json"
        settings.write_text(
            json.dumps({MARKER: {"SessionStart": [{"command": "mine"}]}})
        )
        before = {
            str(p.relative_to(self.project)): p.read_bytes()
            for p in self.project.rglob("*")
            if p.is_file()
        }
        with self.assertRaisesRegex(installer.InstallError, "conflicts"):
            self.install(["claude-code", "antigravity"])
        after = {
            str(p.relative_to(self.project)): p.read_bytes()
            for p in self.project.rglob("*")
            if p.is_file()
        }
        self.assertEqual(before, after)

    def test_interruption_rolls_back_every_destination_and_settings(self):
        self.seed(["claude-code", "antigravity"])
        before = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file() and ".specviz-stage-" not in str(p)
        }
        replace = os.replace
        calls = 0

        def interrupt(source, target):
            nonlocal calls
            if ".specviz-stage-" in str(source):
                calls += 1
                if calls == 3:
                    raise KeyboardInterrupt()
            return replace(source, target)

        with (
            patch("os.replace", side_effect=interrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            self.install(
                ["claude-code", "antigravity"], source=self.stable, channel="stable"
            )
        after = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        self.assertEqual(before, after)

    def test_next_install_recovers_process_interrupted_between_replacements(self):
        directory = self.home / ".specviz/adapters"
        directory.mkdir(parents=True)
        target = self.root / "owned.txt"
        backup = self.root / ".specviz-backup-test"
        stage = self.root / ".specviz-stage-test"
        backup.write_text("original")
        target.write_text("interrupted replacement")
        (directory / "install-transaction.json").write_text(
            json.dumps(
                {
                    "committed": False,
                    "operations": [
                        {
                            "target": str(target),
                            "backup": str(backup),
                            "stage": str(stage),
                            "existed": True,
                        }
                    ],
                }
            )
        )
        with Transaction(directory):
            self.assertEqual(target.read_text(), "original")
        self.assertFalse(backup.exists())

    def test_stable_uninstaller_can_remove_one_shared_beta_registration(self):
        self.seed(["antigravity", "codex"])
        self.install(["codex"], source=self.stable, channel="stable", remove=True)
        target = self.project / ".agents/skills/specviz"
        self.assertEqual(
            json.loads((target / installer.MANIFEST).read_text())["hosts"],
            ["antigravity"],
        )
        self.assertEqual(
            len(json.loads(self.registry("antigravity").read_text())["projects"]), 1
        )

    def test_last_registration_removes_owned_collectors_and_known_cache(self):
        self.seed(["claude-code", "antigravity", "codex"])
        registries = [self.registry(host) for host in ("claude-code", "antigravity")]
        self.install(["claude-code", "antigravity", "codex"])
        for path in registries:
            self.assertEqual(json.loads(path.read_text())["projects"], {})
            self.assertFalse((path.parent / "runtime/specviz_bridge.py").exists())
            self.assertFalse((path.parent / "runtime/specviz/display.py").exists())
            self.assertEqual(list((path.parent / "display").rglob("*.json")), [])
        self.install(["claude-code", "antigravity", "codex"], remove=True)
        self.install(["claude-code", "antigravity", "codex"], remove=True)

    def test_edited_or_referenced_collector_is_retained_with_a_notice(self):
        for case in ("edited", "referenced"):
            with self.subTest(case=case):
                project = self.root / case
                project.mkdir()
                self.seed(["claude-code"], project)
                registry = self.registry("claude-code", project)
                runtime = registry.parent / "runtime/specviz_bridge.py"
                settings = project / ".claude/settings.local.json"
                if case == "edited":
                    runtime.write_text("# my collector modification")
                else:
                    value = json.loads(settings.read_text())
                    value["customCommand"] = str(runtime)
                    settings.write_text(json.dumps(value))
                original = runtime.read_bytes()
                result = self.install(["claude-code"], project=project)
                self.assertEqual(runtime.read_bytes(), original)
                self.assertTrue((runtime.parent / "specviz/display.py").exists())
                self.assertTrue(
                    list((registry.parent / "display").rglob("context.json"))
                )
                self.assertTrue(any(r.get("notices") for r in result))
                self.assertEqual(json.loads(registry.read_text())["projects"], {})

    def test_custom_owned_skill_blocks_migration_and_preserves_other_targets(self):
        self.seed(["codex", "claude-code", "antigravity"])
        changed = self.project / ".agents/skills/specviz/SKILL.md"
        changed.write_text("Custom instructions")
        before = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        with self.assertRaisesRegex(installer.InstallError, "modified"):
            self.install(["codex", "claude-code", "antigravity"])
        after = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        self.assertEqual(before, after)

    def test_unknown_cache_and_other_projects_are_preserved(self):
        self.seed(["antigravity"])
        second = self.root / "second"
        second.mkdir()
        self.seed(["antigravity"], second)
        registry = self.registry("antigravity")
        folder = registry.parent
        note = folder / "display/antigravity" / identity(self.project) / "my-notes.json"
        note.write_text('{"notes":"keep"}')
        other_cache = folder / "display/antigravity" / identity(second)
        before = {p.name: p.read_bytes() for p in other_cache.rglob("*.json")}
        result = self.install(["antigravity"])
        self.assertEqual(note.read_text(), '{"notes":"keep"}')
        self.assertTrue(any(r.get("notices") for r in result))
        self.assertTrue((folder / "runtime/specviz_bridge.py").exists())
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in other_cache.rglob("*.json")}
        )

    def test_retired_beta_requests_create_no_settings(self):
        with self.assertRaisesRegex(installer.InstallError, "retired"):
            self.install(["claude-code"], channel="beta")
        self.assertEqual(list(self.project.iterdir()), [])


# Do not duplicate inherited channel checks in this suite.
for _name in tuple(vars(channels.ChannelTests)):
    if _name.startswith("test_"):
        setattr(AdapterTests, _name, None)


if __name__ == "__main__":
    unittest.main()
