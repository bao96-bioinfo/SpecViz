# Source and adapter contracts

All helper records use `schema_version: 1` and JSON. Unknown versions are
rejected. The existing coding agent supplies semantic understanding; the local
helpers check source coverage and references and render the result. No helper
calls a model service.

## Discovery

`discovery.discover(project=None, selections=None, cwd=None)` returns an inventory:

- `project`: canonical root, checkout identity, name, and purpose.
- `snapshot`: fingerprint of this source inventory.
- `documents`: source snapshots with unique `id`, `path`, `absolute_path`,
  `hash`, retained `text`, `blocks`, framework, group, role, and lifecycle.
- `groups`: identities, readable labels, purposes, framework, and lifecycle.
- `relationships`: `from`, `to`, type, label, and `inferred`. Types are
  containment, reference, workflow dependency, and suggested reading order.
  An unavailable target has `unresolved: true`.
- `scope`: selected document identities; `context`: related identities outside
  the selection. Context does not expand the inspection or comparison scope.
- `warnings`: missing roots, unsupported configurations, and incomplete reads.

Automatic discovery is anchored to a project, rather than the working folder
or a framework's active feature. Use adapter registration for another framework,
with fixtures and compatibility metadata. Never execute configuration or source
commands. Unsupported layouts can be selected explicitly as generic Markdown.

## Immutable sources

`core.snapshot_file(path, root)` retains the exact decoded UTF-8 text, its byte
hash, and blocks with identities, kinds, text, start/end lines, and heading
hierarchy. Blocks preserve lists, tables, code, and unfamiliar constructs.
Repeated headings have distinct locations. A file changing during a read is
rejected. Content hashes identify versions; they are not requirement identities.

`core.default_items(document)` returns conservative section items with original
body text in notes. These are explicitly uninterpreted. Use them when source
meaning is unavailable, rather than making up purpose or behavior.

## Agent interpretation

Read the inventory and source text. Build one interpretation for that snapshot:

```json
{
  "schema_version": 1,
  "snapshot": "inventory fingerprint",
  "project_purpose": "Let people export their reports safely",
  "documents": [{
    "id": "requirements.md",
    "purpose": "Export rules and exceptions",
    "layout": "rules",
    "items": [{
      "id": "export-time",
      "label": "Finish within 30 seconds",
      "kind": "rule",
      "sources": ["requirements.md:L4-6"],
      "notes": ["Encrypted exports are exempt."]
    }],
    "unresolved": [],
    "relationships": []
  }]
}
```

Items need stable identities, readable labels, actual block references, and
comprehensive notes for detailed mode. Layouts are `tree`, `flow`, `interaction`,
or `rules`. Every selected document and substantive source block must be covered
or listed in `unresolved`. Helpers reject invented sources or missing blocks.
Unresolved blocks remain visible with their source content. Structural validation
does not certify the truth of a paraphrase.

Preserve conditions, negations, quantities, units, exceptions, and must/may
differences. Expand unfamiliar abbreviations in labels; exact paths and source
identifiers can remain. Distinguish documented relationships from inferences.
Keep concise and detailed diagrams on the same model and source snapshot.

### Project explanation and concise summaries

Version 1 also accepts `summary` on a document item: optional plain text shown
inside its concise box. Keep `notes` comprehensive for detailed mode. A title
can stand alone; add a sentence when it makes the behavior clearer.

Supply `project_view` for an overview of the project's behavior or components:

```json
{
  "nodes": [{
    "id": "prepare-export",
    "label": "Prepare the report file",
    "summary": "Include at most 100 rows. Encrypt it if the owner requests protection.",
    "sources": [{"document": "design.md", "blocks": ["design.md:L3-3"]}]
  }],
  "relationships": [],
  "unresolved_documents": []
}
```

Use actual inventory IDs in this structure. A relationship has `from`, `to`,
`type`, a readable `label`, boolean `inferred`, and the same source-reference
objects as nodes. Types are `workflow`, `interaction`, `condition`, `containment`,
`reference`, and `reading`; none imply application execution unless the sources
establish it. Every behavioral node and relationship needs real source blocks.
Mark inferences explicitly. Framework-derived document dependencies come from
discovery and must stay distinguishable from behavior.

A collapsed node uses `kind: "group"` and an explicit `members` list of document
IDs. It can omit sources when it only groups those documents. Every scoped
document must occur in a node's sources, group membership, or
`unresolved_documents`. References may include the inventory's related context,
which the view labels separately; they cannot silently widen local scope.

Build the project graph for the requested overview scope. `show` and `changes`
need document interpretations, not a project graph: omit `project_view` from
those models. Reusing a global graph for a local request can correctly fail
out-of-scope reference validation even when its source snapshot is unchanged.

Models without `project_view` remain valid and receive a boxed document map.
Missing project meaning stays unresolved. Structural validation checks identity,
references, and accounting; review the actual sources to establish whether an
explanation is accurate and understandable. This addition changes no source,
requirement, report, or implementation identity.

### Rendering contract

The shared layout module represents a view as measured `Box`, `Graph`, and
`TextBlock` objects. `View.render()` produces ordinary text. Existing public
renderer functions continue returning strings; command rendering can retain the
structured view for pagination. Text is wrapped inside boxes before routing;
completed diagram lines must never be wrapped again.

Graphs use `structure.MapBlock` units when full explanations cannot share a
drawing or page. `Graph.presentation` is shared by `View.render` and pagination:
root map, connected expansions, node/connector keys, then detail panels. Node
keys are assigned by source graph order and are independent of file numbers.
Expanded panels retain a `Diagram N` namespace across file continuations.
Group membership and repeated boundary identities preserve every endpoint;
node-only adjacency prose is never the structural fallback. Compact maps use
distinct ports and explicitly nonjoining `x` crossings. Routing attempts are
bounded to 12 nodes/16 edges, followed by deterministic binary partitioning.
Map geometry is indivisible. Semantic metadata on each map records covered
node and edge identities for verification; it does not certify interpretation. File keys are text blocks with document
identities and a common directory context, printed once per contiguous key.
Only blocks that actually expose a number and its file identity mark that file
as displayed. A behavior box merely referring to a numbered source does not
establish that the file key has already been delivered.

Read [evidence.md](evidence.md) only for implementation reports or comparison;
read [inspection.md](inspection.md) only for explicit code inspection.

### Overview reminder delivery

For a fresh overview, the skill passes internal `--omit-overview-hint` and adds
its contextual reminder in normal chat text after the final helper page. This
option removes only the generic file-selection hint. Direct helper calls keep
that hint by default; JSON inventory, warnings, empty-scope recovery, file keys,
source snapshots, and continuation instructions are unchanged. Other actions
reject the option. `overview_view(..., omit_hint=True)` has the same contract.

Saved pages are immutable, including their original footer. Continuation never
removes old text, even when the option is supplied. Append the new reminder only
when the conversation establishes that this is a completed overview originally
rendered with its hint suppressed. With a legacy view or unknown continuation
context, preserve the saved next step without adding a second footer. No saved
view migration or implementation evidence is involved.

Choose a target from the primary-scope file keys actually delivered, in their
displayed order; inventory order alone does not prove delivery. Related context
is not a local suggestion. A path works without view persistence. A number works
only with this conversation's current, fully delivered key and valid stored
selection; structural `Node` numbers are never file selectors. Empty or
unavailable inventories keep their recovery guidance as the sole next step.

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
