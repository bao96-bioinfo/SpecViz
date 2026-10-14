# Commands

Use `$specviz` in Codex or `/specviz` on the documented Claude Code and
Antigravity surfaces. The rest of the command is the same.

| Arguments | Scope and output |
| --- | --- |
| No arguments, or `overview` | Entire project's specification map |
| `overview <folder>` | Local map, with directly related context labeled |
| `show <file> [more files...]` | Selected file diagrams; multiple files include a relationship map |
| `changes [folder-or-file...]` | Current requests compared with implementation evidence |
| `--detailed` | Comprehensive annotations on the same diagram structure |
| `changes ... --check-code` | Explicit inspection of relevant code and existing test evidence |

Examples (the folder commands use the OpenSpec fixture; the file command uses
the Kiro fixture):

```text
$specviz overview
$specviz overview openspec/changes/password-export
$specviz show requirements.md design.md --detailed
$specviz changes openspec/changes/password-export --check-code --detailed
```

Quote paths containing spaces. Short names work when unambiguous; duplicate
names need their paths. After overview, reply with displayed numbers or names
to select files. Selections stay bound to that conversation's displayed
file map; moved or changed sources require a refresh. When another map is shown,
its delivered file keys become current. Continue to reveal keys hidden on later
pages before selecting their numbers. A folder belongs to
overview; `show` takes files.

The report-based reference persists across displays and sessions. Missing
history is shown as unknown. `--check-code` is independent of detail and scope;
it reads sources without executing tests or changing implementation/task state.
See [comparison meanings](comparison.md) for status and evidence limits.

Large diagrams use counted groups or explicit continuation parts. The agent
keeps the displayed source snapshot while continuing. Related context outside
a local selection does not expand its code inspection or comparison scope.

## Local helper

For contributors and agent integrations, run the bundled helper directly:

```sh
python3 skills/specviz/scripts/specviz_cli.py overview --project /path/to/project
python3 skills/specviz/scripts/specviz_cli.py show "path/with spaces/spec.md" --project /path/to/project --json
```

Direct helper output without an interpretation is a conservative source map.
The installed agent follows the skill to interpret sources, validate coverage,
and print the final explanation. `--model`, `--inspection`, `--event`, and other
exchange flags are documented in the skill references and helper `--help`.
They do not add more user-facing SpecViz actions.


## Fixed display width

Stable uses 80 content columns. Internal `--width` remains a deterministic test
override; automatic width detection and beta enrollment have been retired.
Existing stable continuations keep their stored text. Beta-only tokens request
a fresh stable overview without modifying their old records.

## Current work and historical selection

Ordinary `overview`, `overview openspec/`, `show`, and `changes` automatically
include current specifications and active changes. Known archives are excluded
before numbering, source coverage, and snapshots, including linked archives and
declared external OpenSpec roots. An archived link is not a missing-source warning.
An archive-only project has no current specifications. Names such as
`improve-archive-search` remain active outside the actual archive location.

To inspect history, explicitly select `overview openspec/changes/archive/` or
`show openspec/changes/archive/<dated-change>/design.md`. These sources are labeled
as history; the next ordinary overview again shows current work. Editing history
does not invalidate current file selections. Moving a displayed active source
requires a fresh overview. Historical provenance remains available for report
comparison, but archival alone never establishes implementation.

Large views print their compact structure and node key before explanations.
`Node 2` refers to a component; `show 2` refers only to delivered file `[2]`.
See the [actual ten-file overview](../examples/large-project/overview-page-1.txt).
