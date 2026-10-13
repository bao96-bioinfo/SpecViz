# OpenSpec example

The Reporting service lets report owners export at most 100 rows, with optional password protection. This example shows the OpenSpec document structure; it does not establish that its requested work has been implemented.

From the [fixture project](../../tests/fixtures/frameworks/openspec/project), ask your coding agent:

```text
$specviz overview
$specviz show openspec/changes/password-export/specs/data-export/spec.md
$specviz show openspec/changes/password-export/specs/data-export/spec.md --detailed
```

Claude Code and Antigravity use `/specviz` with the same arguments.

| View | Concise | Detailed |
| --- | --- | --- |
| Project map | [Overview](overview.txt) | [Overview with roles and sections](overview-detailed.txt) |
| Selected file | [File explanation](show.txt) | [Expanded file explanation](show-detailed.txt) |

[model.json](model.json) supplies source-backed interpretation. [selection.json](selection.json) identifies the selected file. Every substantive source block is covered. Detailed notes retain source conditions, numbers, exceptions, optional behavior, and unresolved questions. The [fixture provenance](../../tests/fixtures/frameworks/openspec/provenance.json) records the upstream layout reference.
