# Commands

Use `$specviz` in Codex or `/specviz` on the documented Claude Code and
Antigravity surfaces. The rest of the command is the same.

| Arguments | Scope and output |
| --- | --- |
| No arguments, or `overview` | Entire project's specification map |
| `overview <folder>` | Local map, with directly related context labeled |
| `show <file> [more files...]` | Selected file diagrams, with a relationship map |
| `changes [folder-or-file...]` | Current requests compared with implementation evidence |
| `--detailed` | Comprehensive annotations on the same diagram structure |
| `changes ... --check-code` | Explicit inspection of relevant code and existing test evidence |

For example:

```text
$specviz overview
$specviz overview openspec/changes/data-export
$specviz show requirements.md design.md --detailed
$specviz changes openspec/changes/data-export --check-code --detailed
```

Quote paths containing spaces. Short names work when unambiguous; duplicate
names need their paths. After overview, reply with displayed numbers or names
to select files. Selections stay bound to that conversation's displayed
file map; moved or changed sources require a refresh. When another map is shown,
its displayed numbers become current. A folder belongs to
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
