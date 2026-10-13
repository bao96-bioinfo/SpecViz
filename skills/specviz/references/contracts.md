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

Read [evidence.md](evidence.md) only for implementation reports or comparison;
read [inspection.md](inspection.md) only for explicit code inspection.
