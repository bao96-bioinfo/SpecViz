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
