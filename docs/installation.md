# Installation

Use Python 3.11 or later and an existing coding-agent setup. Get the source:

```sh
git clone https://github.com/bao96-bioinfo/SpecViz.git
cd SpecViz
```

Run the installer from this checkout, selecting the existing project where
specifications live. Replace `/path/to/project` with that project's path:

| Agent | Install command | Invocation |
| --- | --- | --- |
| Codex | `python3 tools/install.py --host codex --project /path/to/project` | `$specviz overview` |
| Claude Code | `python3 tools/install.py --host claude-code --project /path/to/project` | `/specviz overview` |
| Antigravity | `python3 tools/install.py --host antigravity --project /path/to/project` | `/specviz overview` |

Use `--host all` for all three. Codex and Antigravity share the project directory
`.agents/skills/specviz/`; Claude Code uses `.claude/skills/specviz/`. Open a new
coding conversation after installation if the host caches skill discovery.
The installer reports the runtime, scope, version, and changed destinations.
No runtime packages, separate model account, or server are needed.
On Windows, substitute `python` if that is the installed Python 3.11+ command.

## Update and remove

Update your SpecViz checkout with `git pull --ff-only`, then run the same
installation command to copy the new skill into your project. The
installer refuses to replace modified SpecViz files or unrelated skills.
Preserve local modifications before retrying an update. To remove owned files:

```sh
python3 tools/install.py --host all --project /path/to/project --uninstall
```

Unrelated files and local evidence are retained. Compare host surfaces and live
checks in [compatibility](compatibility.md) and [acceptance](acceptance.md).
This release's installer is project-scoped; it does not change global settings.

## Workflow handoffs

Use `--generation-handoff` during installation to enable an explicit workflow
handoff after ready specifications; use `--no-generation-handoff` to disable it.
The ready-artifact callback invokes the same whole-project overview and offers
file selection. The generating agent must invoke the callback; the setting alone
does not install a native lifecycle observer. See the installed
`references/handoffs.md` for each framework's evidence-bearing integration points.

Default comparison reads completion/progress and verification handoffs. The
framework's checked tasks alone do not establish implemented requirement versions.
Comparison state is retained outside the project. `SPECVIZ_STATE_DIR` can relocate
it on a server; select a directory outside the checkout.

## Package

```sh
python3 tools/package.py
```

This builds an ignored `dist/specviz-0.1.0.zip` from the same maintained skill
source, with helpers and references bundled. This ZIP is a standalone skill
bundle; it does not yet include marketplace plugin manifests.
See [marketplace publishing](publishing.md) for the remaining distribution work.
