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

From a stable checkout, this prepares `dist/specviz-0.1.0.zip` and a JSON
checksum receipt. The ZIP includes the complete skill, license, and installer.
After extracting it, run `python3 tools/install.py` with the same arguments as
above. No marketplace plugin manifests are included. Preparing an asset does
not publish it or replace a Git tag.
See [marketplace publishing](publishing.md) for the remaining distribution work.


## Try the adaptive beta

Stable is the default. Adaptive layout is under active development in a separate
`beta` source, version `0.2.0-beta.1`. Beta assets are prepared locally; this guide
does not advertise an unpublished GitHub download or marketplace listing.

From the beta checkout, or an extracted beta bundle supplied by the maintainer:

```sh
python3 tools/install.py --channel beta --host claude-code --project /path/to/project
python3 tools/install.py --channel beta --host antigravity --project /path/to/project
```

Use `--host all` if desired. A default stable command rejects a beta source before
changing the project. The installer never fetches another source or switches
branches. Repeat the beta command from an updated beta source to update beta.
Ordinary `/specviz overview`, `show`, and `changes` commands stay the same.
No width question or terminal setup is required.

Beta targets the interactive Claude Code and Antigravity terminals. An exact
host version/rendering mode needs a verified message-area profile; otherwise it
uses a conservative fallback. **Codex adaptive support is under development**;
Codex retains the stable renderer even when sharing Antigravity's beta skill
folder. Desktop/editor measurement is deferred. See [compatibility](compatibility.md).

### Settings affected by beta

| Host | Configuration scope |
| --- | --- |
| Claude Code | Project `.claude/settings.local.json`: composed status line and SessionStart hook |
| Antigravity | Project `.agents/hooks.json`; user `~/.gemini/antigravity-cli/settings.json`: shared status-line dispatcher |
| Codex | Skill files only; no width provider |

The dispatcher and minimal per-session measurements live outside the checkout
under `~/.specviz/adapters/`. Existing status commands receive their original
input and retain their output. Antigravity's built-in status line is stacked when
no custom line existed. Claude Code's custom-status mode can change its default
footer hints, and periodic callbacks run once per second. Neither adapter stores
raw status payloads, email, or transcript content.

Only registered beta projects collect measurements. Antigravity's dispatcher
stays available while another project needs it. Setup preflights ownership and
uses a recovery journal for interrupted replacement. Later custom status-field
edits survive removal; conflicting edited owned files/hooks require preserving
or reconciling the edit before an update. An inert dispatcher is retained after
unregistration so custom commands referring to it do not break.

### Return to stable

From the **stable checkout or stable bundle**, run:

```sh
python3 tools/install.py --channel stable --host all --project /path/to/project
```

This replaces owned beta skill files and unregisters beta adapters. It restores
only unchanged fields that SpecViz owns, preserving other settings and files.
Open a new coding conversation after switching. Stable saved views and all
implementation evidence remain available. Beta-only continuations require a
fresh stable overview; their records are retained separately.
