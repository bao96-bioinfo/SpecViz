# Reviewing interpretation quality

The helper validates references and content accounting. An agent must still
interpret meaning correctly. Use `tests/fixtures/interpretation/spec.md` as a
source-backed evaluation request: ask a fresh agent to produce concise and
detailed text views using the installed skill. Do not supply an expected diagram.

Check the resulting views against these obligations:

| Source meaning | Review question |
| --- | --- |
| Never export another person's data | Does the explanation retain the prohibition and supplied-identifier exception? |
| 30 seconds; encrypted exports up to 90 seconds | Are both quantities, their units, and the exception visible? |
| Reject over 10 megabytes before creation | Are threshold and ordering retained? |
| Protection optional; chosen passwords at least 12 characters | Are optional choice and conditional minimum distinct? |
| Invalid input creates no partial download | Are the failure outcome and negative condition retained? |
| Role-based access control | Is the unfamiliar abbreviation expanded in explanatory text? |
| Undecided one-day expiry | Is it a question rather than an implemented or mandatory rule? |

Detailed views must account for every source block or show it as unresolved.
Concise views can collapse rules into a named group, with detailed mode exposing
the individual obligations. Check that expanding does not change node order or
relationships. Test judgments of behavioral equivalence separately from syntax
and formatting tests. Record actual host, version, source versions, and observed
limitations in `docs/acceptance.md`; do not treat golden text as model evaluation.

## Review the diagram before reading its source key

Use the eight-file training example under `tests/fixtures/diagram-first/`.
A reader unfamiliar with it should be able to answer:

- What does the project produce, and for whom or for what purpose?
- What happens to the input data, and why are some answers kept separate?
- When may the full training run start? What happens if the small trial fails?
- Which two results meet at evaluation, and what gets saved afterward?
- Which files explain each part? Which decision is still unresolved?

Answers must come from the boxes and connectors. A file tree, a glossary below
the diagram, or a second prose explanation does not repair an unclear diagram.
Check both concise and detailed versions; expansion must retain the logical
nodes and edges. Different wrapping or physical placement is acceptable.

## Explain only what sources support

| Source phrase in the synthetic fixture | Clear explanation supported there |
| --- | --- |
| Persisted split | Save which samples are used for training and evaluation; reuse those assignments when resuming. |
| Fixed recipe | Use the same saved training settings when resuming the run. |
| Smoke gate | Run a small trial first; start full training only if input, training, and saved-output checks all pass. Otherwise stop and report the failures. |
| Acceptance threshold undecided | The acceptable prediction error has not been decided; do not label the model ready. |

These definitions belong to this fixture, not to every project using those
words. For an undefined specialist term, show that its meaning is unresolved
and point to its source. Preserve exact path names and identifiers as keys;
use familiar words or a source-supported expansion in explanations. If a title
already explains the part, an empty optional annotation is better than filler
such as “handle the processing.”

Trace each sentence and arrow back to the referenced blocks. Specifically look
for lost **only if**, **unless**, **not**, quantities, units, optional choices,
and failure outcomes. Read adjacent source blocks: an exception may live below
the paragraph that initially looked complete. A framework's planning order is
a document dependency, not evidence of runtime sequence.

## Negative review cases

The following judgments were checked against the synthetic fixture:

| Candidate box | Verdict and repair |
| --- | --- |
| “Training: fixed recipe, persisted split, smoke gate” | Reject for clarity. Its terms are defined in the source but the reader cannot tell what happens. Replace them with the supported sentences above. |
| “Train the model, then publish it automatically when accuracy exceeds 95%” | Reject for source accuracy. Neither automatic publication nor 95% is specified, and the acceptable error remains undecided. Remove those invented claims and retain the open decision. |
| “Run a small trial before training” | Reject as incomplete if it stands alone: it hides the all-checks-pass condition and stop/report failure outcome. |
| “Save run settings and sample assignments so the run can be repeated” | Accept where linked to the run-records blocks; no extra abstract annotation is needed. |

These are documented semantic reviews, not automated comprehension tests.
Reference validation proves that sources exist, not that a paraphrase is true.
A human reader's feedback is separate evidence and must be recorded as such.

## Contextual overview reminder

Run the installed skill on each project under `tests/fixtures/frameworks/` and
the ten-current-file `tests/fixtures/large-project/project/`. Review the **final
chat**, not only helper output. Expect one or two ordinary sentences after the
completed diagram: one real `show` example and one mention of `--detailed`.
Codex uses `$specviz`; Claude Code and Antigravity use `/specviz`.

| Response-review case | Expected selection and delivery |
| --- | --- |
| OpenSpec overview | `openspec/specs/data-export/spec.md`, the first primary file key; `spec.md` alone is ambiguous |
| Spec Kit overview | `.specify/memory/constitution.md` |
| BMAD overview | `planning/initiative-reporting/epic-data-export/spec-data-export/spec-data-export.md`; a valid displayed number may shorten it |
| Superpowers overview | `docs/superpowers/plans/2026-10-02-data-export.md` |
| Kiro overview | `.kiro/specs/data-export/design.md`, or unique `design.md` |
| Large project overview | `openspec/specs/data-preparation/spec.md`; exclude the eight archived files |
| Local OpenSpec `overview openspec/changes/password-export/specs` | Suggest its `data-export/spec.md` by distinguishing path; related files are context, not targets |
| Temporary copied fixture with spaces, punctuation, or a long path | Quote the literal argument; preserve it in inline code without ellipses or hard wrapping |
| Explicit external source | Preserve the inventory's exact `external::` identity |
| Explicit archived-folder overview | Its delivered historical file is valid; a later ordinary view again selects current work |
| Numbered target | The full file key is delivered in this conversation and unchanged; `Node 1` is never a file selector |
| Missing storage, wrong conversation, or stale number | Use a real path or resolvable unique name; never promise an unavailable number |
| Repeated, detailed, or enabled post-generation overview | Keep the short reminder; no tutorial, menu, question, or automatic `show` |
| Partial delivery, empty scope, or legacy continuation | Keep the existing continuation/recovery/footer; do not add a duplicate reminder |

Reject placeholders such as `[directory/files]`, paths from another project,
excluded archive targets, hidden keys, and `show` with a directory. A valid
resolver result alone does not prove a good suggestion: the file must also
belong to the requested scope and have its key delivered. Check the tool trace
to confirm the suggested exploration was not executed automatically.

`tests/test_overview_guidance.py` exercises these concrete argument examples
against discovery, rendering, and selection. It does not generate agent
responses or certify writing quality. Live host results belong in
[acceptance checks](acceptance.md), including unavailable hosts and actual
multi-page and repeated-request observations.
