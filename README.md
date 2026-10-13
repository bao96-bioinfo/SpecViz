# SpecViz

**Your agent wrote the specs. Start with the map.**

```text
You: /specviz overview

Reporting service - Download reports safely
|
+-- Data export
    |
    requirements.md --> design.md --> tasks.md
    Access and limits   Download flow What to build

SpecViz: Choose a file to explore.

You: /specviz show design.md

Download flow
+-- Not the report owner --> Reject
+-- Report owner --------> Collect up to 100 rows
                          +-- Password given --> Encrypt --> Download
                          +-- No password -----------------> Download
```

SpecViz turns specification files into **text diagrams inside your coding
chat**. See what the project does, how its documents connect, and what each
file means. Start with the big picture; choose when to go deeper.

The conversation above is a shortened illustration of the
[reporting-service example](examples/kiro/README.md). File arrows mean
“guides the next document”; the download flow uses the design and its linked
requirements. Full views include source paths and references.

**Codex · Claude Code · Antigravity**

[Get started](#quick-start) · [Commands](#three-commands-one-workflow) ·
[More examples](examples/README.md) · [Compatibility](docs/compatibility.md)

## Quick start

Requires **Python 3.11+** and your existing coding agent. In a terminal:

```sh
git clone https://github.com/bao96-bioinfo/SpecViz.git
cd SpecViz
python3 tools/install.py --host all --project /path/to/your-project
```

Replace `/path/to/your-project` with the existing project containing your
specifications. For just one agent, replace `all` with `codex`, `claude-code`,
or `antigravity`. On Windows, use `python` if that is your Python 3.11+ command.

Open that project in a new coding conversation and enter:

| Coding agent | First command |
| --- | --- |
| Codex | `$specviz overview` |
| Claude Code | `/specviz overview` |
| Antigravity | `/specviz overview` |

Then pick a file by its displayed number, name, or path. SpecViz waits for
your choice before opening a file view.

The skill uses your existing agent and Python's standard library. Diagrams
appear as ordinary chat text, including when your agent runs on a server.
[Installation, updates, and removal →](docs/installation.md)

## Three commands, one workflow

Examples use `/specviz`; in Codex, use `$specviz` with the same arguments.

| Command | Use it to… |
| --- | --- |
| `/specviz overview` | Get the entire project's specification map. |
| `/specviz show design.md tasks.md` | Explain the files you choose. |
| `/specviz changes` | Compare the current specs with reported implementation. |

Focus on a feature with `/specviz overview openspec/changes/data-export`.
Use full paths when filenames repeat, and quote paths containing spaces.
[All commands and options →](docs/commands.md)

## Choose how much to read

The default view gives you the essentials. Add **`--detailed`** to expand the
same structure with conditions, exceptions, and open questions:

```text
You: /specviz show requirements.md

Export rules
+-- Owner downloads: at most 100 rows
+-- Optional encryption; passwords never logged

You: /specviz show requirements.md --detailed

Export rules
+-- Owner downloads: at most 100 rows
|   When an owner requests a report, export at most 100 rows.
+-- Optional encryption; passwords never logged
    When an owner supplies a password, encrypt the file.
    Never log that password.
```

These excerpts show the two reading depths. `--detailed` works with
`overview`, `show`, and `changes`. Depending on the content, SpecViz uses a
tree, a flow, an interaction diagram, or a rule table.

## See what changed since implementation

A new password requirement touches more than one file. `changes` highlights
it in the feature map and shows the implementation evidence underneath:

```text
You: /specviz changes

Reporting service - Download reports safely
|
+-- Data export [contains changes]
    +-- requirements.md  Export rules        [unchanged]
    +-- design.md        Password protection [changed]
    +-- tasks.md         Add protection      [changed]

Earlier report: File creation implemented.
Password protection: No matching completion evidence.
Verification: Unavailable.
```

This shortened [comparison example](examples/comparison/README.md) uses
workflow completion and verification reports. The comparison stays tied to
reported implementation when you display another diagram. Missing evidence
means **unknown implementation**.

Add `/specviz changes --check-code` to ask your agent to inspect relevant
code and existing test evidence. Inspection reads files without running tests
or changing your implementation.

Reports currently need an explicit SpecViz workflow handoff; native framework
reports are not imported automatically.
[Connect a workflow](docs/installation.md#workflow-handoffs) ·
[Understand the evidence](docs/comparison.md)

## Bring your existing specs

Keep your specification workflow and use SpecViz to explore what it produces:

| Framework | What SpecViz reads | Example |
| --- | --- | --- |
| OpenSpec | Main specs, proposals, designs, and tasks | [Explore](examples/openspec/README.md) |
| GitHub Spec Kit | Feature specs, plans, tasks, and project principles | [Explore](examples/spec-kit/README.md) |
| BMAD Method | Briefs, specifications, tickets, and story plans | [Explore](examples/bmad/README.md) |
| Superpowers | Designs and implementation plans | [Explore](examples/superpowers/README.md) |
| Kiro Specs | Requirements, bugfix specs, designs, and tasks | [Explore](examples/kiro/README.md) |

You can also select other Markdown files for generic views. Framework readers
and agent integrations are separate, making room for more of both.

Live checks cover the terminal interfaces of Codex, Claude Code, and
Antigravity. Desktop and editor interfaces have not been validated.
[Supported layouts and limits →](docs/compatibility.md)

## Explore further

- [Text examples](examples/README.md): full overview and file views at both depths.
- [View guide](docs/views.md): layouts, source references, and large specifications.
- [Contributing](CONTRIBUTING.md): project structure, development, and tests.
- [Marketplace publishing](docs/publishing.md): the path to plugin distribution.

**Available now:** install the skill from this repository. Marketplace
packages and listings are still to come.

To run the test suite from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

Contributions to framework support and clearer diagrams are welcome.
Licensed under [Apache 2.0](LICENSE).
