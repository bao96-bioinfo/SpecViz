# Semantic comparison records

The first `changes --json` request returns retained workflow evidence and current
source blocks. Build an interpretation for the current inventory, and add
`comparisons` where wording or requirement identity changed.

Each entry identifies `document`, current `requirement_id`,
`evidence_document`, `evidence_requirement_id`, and the actual `evidence_id`.
Include `classification` (`equivalent`, `behavioral`, `removal`, or `unclear`),
`reason`, `sources` containing every current item's source block identity,
and `prior_text` copied exactly from its retained coverage. The helper validates
the correspondence against the latest applicable evidence, not a chosen older
report. See the returned rows for the event and requirement identities.

`equivalent` means obligations, conditions, outcomes, limits, and exceptions
remain the same. `behavioral` means one of those changed. `removal` requires an
explicit current request to remove the earlier behavior. Missing files alone
remain unresolved. Use `unclear` if the source does not establish equivalence.

Keep requested differences and implementation evidence distinct. Earlier code
can support the old behavior while the new requirement remains outstanding.
Report verification only when a version-applicable execution report exists.
Code edits can make evidence stale; newly edited requested specifications do not
by themselves erase the valid earlier implemented reference.

## Historical sources

Ordinary comparisons exclude archived planning documents from presentation,
while retaining all completion reports and inspection records. Known archive
paths do not become missing-source warnings. An active-to-archive move is
recognized only when its declared change lineage has one candidate whose bytes
match the retained report version. Ambiguous moves and unexpected active-source
deletions remain unresolved. Basenames and checked tasks are insufficient.

A current requirement can use an older report through the existing explicit,
source-backed correspondence contract. Its verification limits remain visible;
other current requirements remain unknown. Merely viewing either version never
records completion. Both current and indexed historical specifications are
excluded from implementation fingerprints; relevant code edits still stale
evidence. Historical content is loaded only for explicit viewing or provenance
checks, not added to the current explanation.
