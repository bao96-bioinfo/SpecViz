# Reading SpecViz views

SpecViz returns fixed-width text in the conversation. Every view starts with the project purpose and source snapshot. File numbers refer to that displayed inventory; use a full path when the conversation does not retain its selection.

## Start with the map

```text
Reporting service - Export reports safely
|
+-- Data export (3 files)
    +-- [1] requirements.md - Export rules
    +-- [2] design.md       - How export works
    +-- [3] tasks.md        - Implementation steps
```

`overview` shows the whole project. `overview <folder>` selects a local scope and labels related files outside it as context. The map lists every discovered file, grouped by purpose, with counts. Archived specifications appear as history. Discovery warnings identify unavailable or unsupported content.

## Explore selected files

`show <file> [more files...]` displays their relationship map and content. The same node labels and order appear with `--detailed`; notes expand beneath the existing nodes.

Layouts follow the source meaning:

| Layout | Useful for | Reading rule |
| --- | --- | --- |
| Hierarchy | Goals, document organization, grouped decisions | Branches mean membership, not execution order. |
| Flow | Ordered behavior | Read the labeled arrows; an arrow states its relationship. |
| Interaction | Requests between people or components | Each arrow names the interaction. |
| Rules | Independent permissions and conditions | Rows do not imply a sequence. |

Source annotations retain full paths, line ranges, and section names. Inferred relationships are labeled. Unfamiliar abbreviations should be expanded by the interpreting agent; exact filenames and source identifiers remain available for reference.

## Know what is established

Without an agent interpretation, the helper shows source sections as **unresolved**. Detailed mode retains their original wording, including numbers, exceptions, optional behavior, and unanswered questions. A readable structure does not establish that the source has been understood correctly.

`changes` compares requested behavior with retained implementation evidence. `[changed]` marks a requested difference, and `[contains changes]` marks its parent group. `[attention]` and `[contains attention]` mark incomplete or uncertain evidence. A missing report means **implementation unknown**. Completion, verification, and optional code inspection remain distinct.

The default comparison keeps behavior labels, short reasons, and evidence limits in the diagram. Code contradictions and uninspected scope remain visible. Add `--detailed` for full requested and earlier requirement wording, source versions, report provenance, verification outcomes, and inspected locations. Concise mode summarizes those details; it does not claim to reproduce all source text.

Long labels wrap within 80 columns. Large responses identify their part, remaining content, and source snapshot. Continue that snapshot to finish reading; refresh after source edits. Only the final part says that all selected content has been delivered.

See [maintained examples](../examples/README.md) for the five supported specification frameworks.
