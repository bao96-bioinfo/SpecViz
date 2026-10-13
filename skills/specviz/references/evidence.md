# Evidence handoffs

`changes` compares the currently requested source with what a workflow actually
reported implementing. Displaying any diagram neither records completion nor
changes the reference. Capture exact specifications when a round begins, then
retain those versions until an explicit report identifies another implemented
version. A paused or retried apply uses the same `round_id`.

For duplicate delivery, replay the original handoff JSON. Stored receipts add
checkout identity, recording time, and derived coverage metadata; they are
query results rather than portable replay inputs. Reusing an event identifier
with a changed payload is rejected and never overwrites history.

## Supported origins

All five adapters support **SpecViz schema 1 explicit handoffs**. Their origin is
`handoff`, with the actual chat/report reference in `origin.source`. OpenSpec
apply, Spec Kit implementation phases, BMAD builds, Superpowers execution, and
Kiro task execution are distinct workflows; their command names do not prove
completion. Native persisted reports and automatic lifecycle hooks are currently
unsupported. Installed skills can capture reports through the documented
handoff contract; unavailable capture leaves implementation unknown.

The five fixtures in `tests/fixtures/reports/` demonstrate this contract and link
the upstream workflow descriptions. They are synthetic schema-1 handoffs, not
representations of proprietary or universally available native report formats.

## Event contract

```json
{
  "schema_version": 1,
  "event_id": "export-completion-2",
  "event": "complete",
  "framework": "openspec",
  "round_id": "export-round-1",
  "occurred_at": "2026-10-12T00:00:00+00:00",
  "scope": ["Data export"],
  "origin": {"kind": "handoff", "source": "chat:completion-2", "host": "codex"},
  "specifications": [],
  "implementation": {"files": {}, "complete_manifest": false},
  "coverage": [],
  "declared_complete": true
}
```

This minimal event reports scope completion without claiming version-bound
requirement coverage. Meaningful coverage additionally requires:

- `specifications`: `{path, hash, text}` objects retaining exact source text and
  its SHA-256 fingerprint. Paths are relative to the project. A `begin` event may
  retain these sources for later events in that same round.
- `coverage`: `{requirement_id, document, spec_hash, text, status, sources?, details?}`.
  Covered text must occur in the matching retained source, or exactly assemble
  its cited `sources` through `requested_text(item, document)`. Preserve relevant
  headings; a heading can contain a normative limit. Status is
  `implemented`, `partial`, or `task-progress`. Missing version binding stays
  uncertain; checked tasks are progress alone.
  Source blocks distinguish top-level list items while retaining nested children
  with their parent. Cite the actual inventory block identities rather than
  copying line ranges from an older parser output. Retained text and source
  hashes remain the authority when an unreleased block identifier changes.
- `implementation`: `{files: {relative_path: sha256}, revision?,
  complete_manifest: boolean, excluded_specifications?: [relative_path]}`. Fingerprint relevant code, including dirty
  files. Without established relevant paths, use the helper's conservative
  manifest and disclose that unrelated source changes may invalidate it.
  Pass discovered specification paths to `implementation_identity(...,
  specification_paths=[...])` so planning documents are excluded even when a
  configurable framework root contains TOML or other non-Markdown artifacts.
  Comparison also excludes retained specification paths and currently discovered
  documents from effective fingerprint checks. This does not rewrite old records:
  a specification edit alone cannot stale its earlier implementation reference.

Events are `begin`, `progress`, `complete`, `verify`, and
`specifications-ready`. Only `complete` with `declared_complete: true` closes a
round. A BMAD report labeled `built` must use progress until actual completion
is reported. Synchronization, archival, and `specifications-ready` never create
implementation completion. Each event must have a unique stable identifier;
repeating identical delivery is safe, while conflicting reuse is rejected.
Use `occurred_at` to retain the actual workflow time when handoffs may arrive
late. Competing records with complete workflow timestamps are ordered by that
time; otherwise delivery order and its limitation are disclosed. `recorded_at`
is persistence time, never invented workflow chronology.

Verification is separate: `{executed: true|false, checks: [{command, result}]}`.
These are descriptions of already reported runs, never commands for SpecViz to
execute. Test definitions found in code do not constitute a run. Verification
attachments match the same round and implementation fingerprints.

## Local retention

SQLite history is outside the repository: macOS uses
`~/Library/Application Support/SpecViz/`, Windows uses
`%LOCALAPPDATA%/SpecViz/`, and Linux uses `$XDG_STATE_HOME/specviz/` or
`~/.local/state/specviz/`. `SPECVIZ_STATE_DIR` relocates state for servers and
tests; it must remain outside the project.

Canonical root and Git worktree identity isolate databases. Agents in the same
checkout share history; copied checkouts do not inherit it automatically.
Immutable events survive inspection and later specification edits. Source drift
makes current applicability uncertain while retaining the earlier evidence.
SQLite transactions prevent partial writes, and unsupported schema versions
are rejected without replacing history. Retention has no automatic expiry;
removing the skill does not implicitly delete evidence.

## Independent inspection

Inspection records contain `schema_version`, `inspection_id`,
`observational: true`, `tests_executed: false`, `complete`, `scope`, specification
fingerprints, implementation fingerprints, and `findings`. Each finding names
its `requirement_id`, `document`, `status`, `reason`, inspected `locations`
(`{path, line}`), and `uninspected` portions.

Allowed statuses are `supported`, `partial`, `contradicted`, `not-found`, and
`unclear`. Supporting or contrary claims require fingerprinted source
locations. Full support cannot include uninspected requirement portions.
Incomplete results remain scoped and offer continuation. Keyword search
failure means not found in the inspected scope, never proven absent throughout
the project. Findings do not close rounds, overwrite reports, or run tests;
cached findings require unchanged specification and code fingerprints.
Persisted inspection of declared `external::` specification sources is currently
unsupported and produces an explicit limitation. Their workflow report comparison
and text views remain available. Implementation fingerprints must name local
project sources; external code fingerprints are also unsupported.
