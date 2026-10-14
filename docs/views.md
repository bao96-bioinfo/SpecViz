# Reading SpecViz views

## Text box grammar

Connected diagrams use `+`, `-`, and `|` for closed box borders and ASCII arrows
(`>`, `<`, `v`, `^`) for direction. A title identifies the subject; a sentence
inside the box explains its action, condition, or result when needed. Box text
wraps before borders are drawn, preserving the full explanation and source
characters. The default is 80 display columns; narrow views stack vertically.
Wide characters count as two columns and combining marks stay with their text.

Arrows name the relationship they express: a request, a result, a planning
dependency, or membership. Branches and joins share boxes. Independent rules
remain independent; document planning never establishes runtime order. A `*`
marks an inferred connector and refers to one short legend. When explanation boxes cannot fit, a compact structural map precedes their
expanded panels. A crossing marked `x` does not join the wires. These node keys are distinct from
the square-bracketed file numbers used by `show`.

SpecViz returns fixed-width text in the conversation. The project purpose leads
into connected boxes explaining its main parts. File numbers refer to that
displayed inventory; use a full path when the conversation does not retain its
selection. Full snapshot hashes stay in detailed output and structured state.

## Start with the map

`overview` shows the whole project. `overview <folder>` selects a local scope
and labels related files outside it as context. With an agent interpretation,
the diagram explains how the project's parts fit together. A compact file key
connects those boxes to selectable documents. Without that interpretation, a
boxed document map shows the known organization and identifies missing meaning.

Every eligible file is represented directly or in a counted group. Archived
specifications appear only when explicitly selected as history. Discovery warnings identify unavailable or
unsupported content. The [eight-file example](../examples/diagram-first/README.md)
includes a training branch, separately held evaluation answers, and their join.

The file key prints a shared directory once and keeps enough of each relative
path to distinguish repeated names, for example `specs/data-preparation/spec.md`
and `specs/evaluation/spec.md`. Numbers stay bound to the full inventory, even
in local views. Related outside-scope files are explicitly marked as context.
Large groups show counts and a file key that can continue across response
parts; no files disappear merely because the diagram groups them.

## Explore selected files

`show <file> [more files...]` displays a relationship map for multiple selected
files, followed by their content diagrams. A single selected file opens directly
into its content. The same node labels and relationships appear with
`--detailed`; notes expand inside or beneath the relevant boxes. Geometry can
grow or reflow while node identities and relationship meanings stay the same.

Layouts follow the source meaning:

| Layout | Useful for | Reading rule |
| --- | --- | --- |
| Hierarchy | Goals, document organization, grouped decisions | Branches mean membership, not execution order. |
| Flow | Ordered behavior | Read the labeled arrows; an arrow states its relationship. |
| Interaction | Requests between people or components | Each arrow names the interaction. |
| Rules | Independent permissions and conditions | Rows do not imply a sequence. |

The file key resolves numbers to exact paths. Box annotations give source line
ranges; detailed mode adds headings and comprehensive notes. Inferred
relationships are marked with `*`. Explain unfamiliar terms only when their
meaning is supported by the source; exact filenames remain available as
references. A clear sentence is preferable to an opaque short phrase.

## Know what is established

Without an agent interpretation, the helper shows source sections as **unresolved**. Detailed mode retains their original wording, including numbers, exceptions, optional behavior, and unanswered questions. A readable structure does not establish that the source has been understood correctly.

Earlier interpretation models still work. When they have no project explanation,
the overview draws their known document organization and explicitly identifies
the missing project meaning. A framework's inferred document dependency is
labeled as such; it never establishes the order in which the application runs.

`changes` compares requested behavior with retained implementation evidence. `[changed]` marks a requested difference, and `[contains changes]` marks its parent group. `[attention]` and `[contains attention]` mark incomplete or uncertain evidence. A missing report means **implementation unknown**. Completion, verification, and optional code inspection remain distinct.

The default comparison keeps behavior labels, short reasons, and evidence limits in the diagram. Code contradictions and uninspected scope remain visible. Add `--detailed` for full requested and earlier requirement wording, source versions, report provenance, verification outcomes, and inspected locations. Concise mode summarizes those details; it does not claim to reproduce all source text.

Long labels wrap within 80 columns. Large responses identify their part and remaining content, and retain the source snapshot in state. Continue that snapshot to finish reading; refresh after source edits. Only the final part says that all selected content has been delivered.

See [maintained examples](../examples/README.md) for the five supported specification frameworks.

## Long diagrams and continuation

A page keeps each box closed. Large graphs retain an overall structural map
before numbered detail panels; long notes continue in closed boxes with the
same node key. Root maps and connected expansions are whole semantic units.
When a map cannot fit even compactly, counted layout groups expand before any
verbose panels. Repeated boundary keys refer to the same component. The part count and next-section notice show what
remains. Follow the printed `--continue-view` command with the same conversation
`--session`; this uses the original source snapshot. Changes to those sources
require a refreshed view. The full snapshot hash appears only in detailed
references or structured state.

`--max-lines 12` is the smallest helper page budget (the follow-up command is
printed separately). File keys repeat their shared directory when a new page
needs it. A number becomes selectable only after its complete key is delivered.
Seeing a group count or a `Files: [n]` reference does not expose hidden members.

Earlier saved text pages remain readable. If state cannot be saved, the helper
shows the complete view and asks for path-based selection. If a saved view can
be read but delivery cannot be recorded, continuation still works; newly shown
numbers are not activated. Neither path creates implementation evidence.

## Compact structure and bounded routing

The [large-project example](../examples/large-project/README.md) has ten current
files, seven components, and eight connections. Its complete structure and node
key fit on the first 80-column, 100-line page. Explanation length does not affect
that structure. Small complete diagrams need no duplicate summary map.

The router tries at most 12 nodes and 16 edges in one drawing. It first tries a main process with side inputs or outputs, then a compact
row when it fits, otherwise separate connector lanes. Every edge gets distinct
ports; crossing wires never create an unstated junction. Feedback, more than
two branches, joins, and isolated nodes retain their actual connections. Larger
graphs split into counted layout groups recursively, then show connected
expansions and boundary maps. Group membership is explicit; layout grouping
does not assert a new application component. Work is bounded by
`O((nodes + edges) log nodes)` plus emitted text, without routing search.

Node keys and full labels connect maps to panels. Connector keys retain type,
condition, direction, and inference markers; source notes and change markers
remain attached to the same identities. Even at 24 columns and 12 lines per
page, structural maps remain closed and expansions precede explanations.
The public helper retains its minimum width of 30 columns. Width defaults to
80; no terminal or chat width is detected.

The [feedback example](../examples/large-project/feedback.txt) is rendered by
the same compact path, including its return arrow and condition.
