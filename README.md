# SpecViz

**Understand the specification before reading every file.**

SpecViz turns specification documents into text diagrams inside your coding
chat. See the whole project first, choose the files that matter, and expand
the detail when you need it. Diagrams stay readable in a terminal or remote
session, with everything shown directly in the conversation.

[Quick start](#quick-start) · [Commands](#three-commands-to-remember) ·
[Examples](examples/README.md) · [Marketplace publishing](docs/publishing.md)

```text
Reporting service - Download reports safely
|
+-- Data export
    +-- [1] requirements.md  Who can download, and what is allowed
    +-- [2] design.md        How files are created and protected
    +-- [3] tasks.md         Steps to build and verify the feature

Choose a file by number, name, or path to explore it.
```

Shortened example. Full views include source paths and references. SpecViz
offers the next level and waits for your selection.

## What you can do

| When you need to… | SpecViz helps you… |
| --- | --- |
| Understand an unfamiliar project | See features, specification files, their purposes, and relationships. |
| Focus on one feature | Scope the overview to a folder while keeping related context visible. |
| Read a specification | Explore selected files as trees, flows, interaction diagrams, or rule tables. |
| Check the finer points | Add `--detailed` for expanded requirements, conditions, exceptions, and open questions. |
| Review specification changes | Highlight affected features and files against reported implementation. |
| Investigate implementation gaps | Add `--check-code` to inspect relevant code and existing test evidence. |

## Quick start

You need **Python 3.11+** and an existing Codex, Claude Code, or Antigravity
setup. SpecViz uses your coding agent; its Python helpers need no extra packages
or separate service.

### 1. Get SpecViz

```sh
git clone https://github.com/bao96-bioinfo/SpecViz.git
cd SpecViz
```

### 2. Install into your project

Replace `/path/to/your-project` with the existing project containing your
specifications:

```sh
python3 tools/install.py --host all --project /path/to/your-project
```

To install for one agent, replace `all` with `codex`, `claude-code`, or
`antigravity`. On Windows, use `python` if that is your Python 3.11+ command.

Installation applies to the selected project. Open that project in your coding
agent and start a new conversation so it can discover the skill.

### 3. Ask for the overview

Type this **in your coding chat**:

| Agent | First command |
| --- | --- |
| Codex | `$specviz overview` |
| Claude Code | `/specviz overview` |
| Antigravity | `/specviz overview` |

Then choose a file from the displayed map. You can also start with just
`$specviz` or `/specviz`.

[Installation, updates, and removal →](docs/installation.md)

## Three commands to remember

These examples use Claude Code and Antigravity's `/specviz` prefix. In Codex,
use `$specviz` with the same arguments.

| Command | What you see |
| --- | --- |
| `/specviz overview` | The entire project's specification map. |
| `/specviz overview openspec/changes/data-export` | A local overview of that change. |
| `/specviz show design.md tasks.md` | Diagrams for the selected files. |
| `/specviz changes` | Specification differences against implementation evidence, grouped by feature and file. |

**Start small, expand when needed:**

```text
/specviz overview
/specviz show design.md
/specviz show design.md --detailed
/specviz changes --check-code
```

`--detailed` works with all three actions. `--check-code` works with `changes`
and can be combined with `--detailed`. Use full paths when filenames repeat;
quote paths containing spaces. After a map, you can select its displayed
numbers instead of typing paths.

[Full command reference →](docs/commands.md)

## How implementation comparison works

`changes` compares today's specifications with the applicable requirement
versions reported as implemented by your workflow. Verification results appear
separately. Viewing a diagram preserves that reference across conversations.

```text
Data export [contains changes]
+-- requirements.md  Export rules        [unchanged]
+-- design.md        Password protection [changed]
+-- tasks.md         Add protection      [changed]

Earlier report: File creation implemented.
Password protection: No matching completion evidence.
Verification: Unavailable.
```

This shortened example shows why a change needs attention. Missing evidence
means **unknown implementation**, rather than proof that work is unfinished.

Reports currently enter through an explicit SpecViz workflow handoff. Native
reports from every framework are not imported automatically. If you have no
handoff history, use `changes --check-code` for an independent inspection of
code and existing test evidence. It reads files without running tests or
changing your implementation.

[Comparison details](docs/comparison.md) ·
[Connect a workflow](docs/installation.md#workflow-handoffs)

## Supported specification frameworks

| Framework | Typical documents |
| --- | --- |
| OpenSpec | Main specifications, change proposals, designs, and tasks. |
| GitHub Spec Kit | Feature specifications, plans, tasks, and project principles. |
| BMAD Method | Initiative briefs, feature specifications, tickets, and story plans. |
| Superpowers | Design documents and implementation plans. |
| Kiro Specs | Feature requirements, bugfix specifications, designs, and tasks. |

Explicitly selected Markdown files can also receive generic views. Readers
and host integrations are separate, so new frameworks and coding agents can
be added without duplicating the visualization logic.

All five frameworks have reproducible [text examples](examples/README.md).
Live checks cover the terminal interfaces of all three coding agents; desktop
and editor interfaces have not been validated.
See [compatibility and limits](docs/compatibility.md) for supported layouts.

## Find your way around

| Resource | Start here for… |
| --- | --- |
| [Installation](docs/installation.md) | Setup, updates, removal, and workflow connections. |
| [Commands](docs/commands.md) | Scope, file selection, and detail options. |
| [Text examples](examples/README.md) | Overview and file diagrams for each framework. |
| [Marketplace publishing](docs/publishing.md) | Distribution plans for Claude Code, Codex, and Antigravity. |
| [Contributing](CONTRIBUTING.md) | Repository structure, development, and tests. |

**Distribution status:** install from this repository using the steps above.
Marketplace plugin packages and public listings are not yet available.

## Contributing

The maintained skill is in `skills/specviz/`, development tools are in
`tools/`, and tests and fixtures are in `tests/`.

```sh
python3 -m unittest discover -s tests -v
```

Contributions to framework readers, host support, and clearer text examples
are welcome. Read the [contributor guide](CONTRIBUTING.md) before making changes.

## License

[Apache 2.0](LICENSE).
