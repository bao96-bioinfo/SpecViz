# Installation

Use Python 3.11 or later and an existing coding-agent setup. Get the source:

```sh
git clone --branch main https://github.com/bao96-bioinfo/SpecViz.git
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
Stable installation adds no display hooks or status-line settings. Uninstalling
one host retains another host registered in the same skill directory.

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

From a stable checkout, this prepares `dist/specviz-0.1.1.zip` and a JSON
checksum receipt. The ZIP includes the complete skill, license, and installer.
After extracting it, run `python3 tools/install.py` with the same arguments as
above. No marketplace plugin manifests are included. Preparing an asset does
not publish it or replace a Git tag.
See [marketplace publishing](publishing.md) for the remaining distribution work.


## Return from retired beta

Adaptive beta `0.2.0-beta.1` has been retired. New installation, packaging, and
release commands accept only stable; `--channel stable` remains optional.
Run this from a **current stable checkout or extracted stable bundle**:

```sh
python3 tools/install.py --channel stable --host all --project /path/to/project
```

No beta checkout or runtime is required. Alternatively, remove the old install:

```sh
python3 tools/install.py --host all --project /path/to/project --uninstall
```

Migration replaces only owned skill files and unregisters the selected project's
old callbacks. Codex and Antigravity share one skill directory: updating either
updates that shared copy; uninstalling one leaves the other's registration.
Other projects' Antigravity registrations keep their dispatcher until removed.

Cleanup restores unchanged owned fields in project `.claude/settings.local.json`,
project `.agents/hooks.json`, and user `~/.gemini/antigravity-cli/settings.json`.
The last registration removes unmodified owned collectors and recognized
session measurement caches under `~/.specviz/adapters/`. Edited collectors or
collectors still referenced by custom host settings are retained with a notice.
Unknown cache files are also retained. Conflicting edits to owned skill files
or hooks stop the transaction with the affected path or setting identified;
preserve or reconcile those edits before retrying. Interrupted writes roll back.

Open a new coding conversation after migration. Saved stable pages keep their
original text and file numbers. Beta-only continuation tokens ask for a fresh
stable overview; their records, source snapshots, completion reports, and code
inspection evidence remain unchanged. Removing the maintained beta distribution
cannot remotely remove copies that readers already downloaded.
