# Comparing specifications with implementation

Use `/specviz changes` (Codex: `$specviz changes`) for the entire project. Add
paths to select a feature or files. `--detailed` adds the previously implemented
text, requested text, sources, and reason. `--check-code` explicitly asks the
agent to inspect relevant code and existing tests without executing them.

Changes use the same text boxes and document connectors as other views. Group
and file boxes retain unchanged context while marking requested changes or
uncertain evidence. Each behavior box keeps its evidence status, explanation,
and verification limits together. Detailed mode expands that same claim with
retained wording and report or inspection sources. No display creates a report.

## What the labels mean

| Label | Meaning |
| --- | --- |
| Reported implemented | A workflow report binds coverage to retained source and matching code fingerprints |
| Partial | The report covers part of the requirement; remaining obligations are not confirmed |
| Task progress | Task activity is recorded without asserting requirement compliance |
| Unknown | Applicable implementation evidence or version bindings are missing |
| Stale | Relevant implementation files changed since the report or inspection |
| Code supported / code partial | Optional inspection supports the requirement within its recorded scope |
| Contradicted | Optional inspection supplies contrary evidence; reports remain visible |
| Not found | Behavior was not located within the inspected scope |
| Unclear | Inspection or source correspondence cannot establish a conclusion |

Verification is an additional fact. Reported completion does not imply tests
passed, and code support does not establish a test run.

## Earlier implementation, newer requested behavior

```text
File [2]: design.md

+------------------------------------------------------------------------------+
| [changed] Export design                                                      |
|                                                                              |
| Difference: behavioral                                                       |
| Evidence status: Earlier behavior reported implemented                       |
| Password protection adds a requested obligation to earlier file creation     |
| Earlier behavior verification: Unavailable; passing checks are not           |
| established.                                                                 |
+------------------------------------------------------------------------------+
```

The earlier implemented text remains the reference when specifications change.
A later valid report clears only the requirements it covers. Displaying this
diagram repeatedly never clears the difference. Relevant code drift retains
the historical text but makes its present applicability uncertain.

Planning documents are excluded from implementation fingerprints using both
retained source versions and the current discovered inventory. This applies to
explicit generic files and configurable framework roots, including BMAD ticket
collections. Specification edits alone preserve the older implementation
reference; changes to actual application sources still make it stale.

## Missing reports and partial completion

See the [complete report-based output](../examples/comparison/reports.txt)
for implemented and changed behavior in the same map. Each box carries its own
evidence and verification limits; unknown and partial states are not completion.

Missing history does not demonstrate unmet behavior. The existing project may
already implement it. A report for one feature or one part of a requirement does
not establish completion for other parts, features, or competing proposals.

## Document changes versus behavior changes

The helper recognizes identical retained text and plain-prose spacing or wrapping
with unchanged block structure. Whitespace inside quoted literals, code,
nested lists, tables, or unfamiliar constructs remains unresolved without
source-backed semantic review.
Other rewording, renamed sections, moved files, or archival changes require a
source-backed agent correspondence. If meaning is unclear, it stays unresolved.
Conditions, limits, units, exceptions, and negations must survive equivalence
review. A missing source alone never requests code deletion; an explicit
withdrawal must be mapped to the prior requirement identity.

An interpretation may supply `comparisons` alongside its normal documents:

```json
{
  "document": "requirements.md",
  "requirement_id": "requirements.md#export-rules:1",
  "evidence_id": "export-completion-1",
  "evidence_requirement_id": "requirements.md#export-rules:1",
  "evidence_document": "requirements.md",
  "classification": "behavioral",
  "sources": ["requirements.md:L3-3"],
  "prior_text": "Create export files.",
  "reason": "Password protection adds an obligation absent from the prior version"
}
```

Classifications are `equivalent`, `behavioral`, `removal`, and `unclear`. Source
references must account for all references of the current item, and prior text
must match actual retained evidence. Include normative headings in covered
source spans using `requested_text(item, document)`. Optional
`requested_hash` binds correspondence to a current version. The helper validates
structure and provenance; human or agent review must evaluate meaning. It
rejects invented sources and comparisons against superseded reports.

## Reports and inspection can disagree

```text
File [2]: design.md

+------------------------------------------------------------------------------+
| [changed] Export design                                                      |
|                                                                              |
| Difference: behavioral                                                       |
| Evidence status: Current code contradicts requested behavior                 |
| The password guard raises an error instead of protecting the file; current   |
| code contradicts retained workflow completion evidence                       |
| Verification: Unavailable; passing checks are not established.               |
| Code finding: contradicted                                                   |
| Inspection limit: Observation only; workflow rounds unchanged and tests were |
| not executed.                                                                |
+------------------------------------------------------------------------------+
```

Inspection is separate history, so this discrepancy never rewrites the original
completion report. A stale saved finding cannot confirm current behavior.
Incomplete inspection identifies uninspected portions and offers continuation.
Ordinary `changes` uses reports; inspection findings appear only when requested
with `--check-code`.

When an applicable inspection supports the current requirement, the current gap
clears even if the older workflow report covers different behavior. The
historical report text, report comparison, source versions, and verification
limits remain separate. A contradicted current requirement becomes a code-backed
gap. Partial or unclear inspection retains the unresolved portions and prior
report comparison; it never creates a completion report.

Competing version-bound reports without complete workflow timestamps do not
establish which implementation is newest. SpecViz retains the candidate report,
alternatives, and source differences while marking their temporal ordering
uncertain. Supply actual `occurred_at` timestamps for reports that arrive late;
delivery order alone cannot establish a current unmet requirement.

External specification roots retain text views and workflow-report comparisons.
Persisted code inspection for `external::` sources is currently unsupported and
reports that limitation explicitly. Local source inspection remains available.

See [evidence handoffs](../skills/specviz/references/evidence.md) for persistence,
source versions, and the tested explicit handoff formats. There is no comparison
baseline based on the last display.
