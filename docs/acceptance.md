# Acceptance checks

Earlier host checks recorded on October 12, 2026. Diagram-first checks below
were recorded on October 13, 2026. Automated fixtures, live coding hosts,
language interpretation, and reader feedback are separate evidence.

## Connected overviews and beta retirement — October 14, 2026

The synthetic large-project fixture has 18 source files: five current rules,
five active-change files, and eight historical files. Before the change it
produced 18 displayed files and separate panels without an overall map. The
maintained [new example](../examples/large-project/README.md) displays ten files
and draws all seven components and eight directed relationships first.

Automated checks trace actual connector characters, including branches, joins,
long edges, feedback, and nonjoining crossings. Dense 40-node graphs, isolated
nodes, and minimum 24-column/12-line internal budgets retain bounded structural
expansions before details. Node keys remain distinct from selectable file keys;
continued file graphs retain their diagram namespace. These are structural and
source-accounting checks, not evidence of reader comprehension.

Legacy installation fixtures are independent of the beta checkout. They cover
shared Codex/Antigravity files, multiple projects, custom status fields, edited
hooks/collectors, retained external references, transaction interruption,
repeated removal, old stable pages, beta refresh notices, and unchanged evidence.
An extracted stable ZIP also passed migration, update, ten-file discovery,
uninstall, and repeat removal without its original beta source.

Local Python 3.11 and 3.14 validation, remote CI results, live-host observations,
and the final branch-retirement result are recorded in
[the change acceptance record](connected-overview-acceptance.json).

Live reproduction uses an isolated copy of the source fixture and an ordinary
installed skill, without supplying the reviewed example model or expected text:

```sh
python3 tools/overview_acceptance.py --host codex
python3 tools/overview_acceptance.py --host claude-code
python3 tools/overview_acceptance.py --host antigravity
```

Review each recorded chat response; a zero process status alone is insufficient.
Antigravity 1.3.4 returned an empty response when headless command permission was
denied, so that invocation is recorded as unavailable, not passed. No global
permission bypass was enabled. Initial Codex and Claude Code runs showed ten
eligible files and a map before panels; Claude's redundant footer prompted a
focused delivery-instruction revision and another live check.

The subsequent Codex and Claude Code responses retained connected maps before
panels, ten eligible files, matching keys, proposed-work qualifications, and one
selection hint. Claude's final response stopped after the helper output. These
live checks preceded the final continuation-title namespace refinement; the
sealed candidate passed 206 tests on each local Python version and all six
[CI jobs](https://github.com/bao96-bioinfo/SpecViz/actions/runs/38617026141).

The reader reviewed the new compact seven-node map and answered **“Clear
enough.”** This is qualitative feedback on that example, not a usability study.
Adaptive-beta measurements below are historical only.

After stable CI passed, the expected beta tip was rechecked. The worktree had no
unexpected local work. The remote/local beta branch, local worktree, and known
beta ZIP/receipt were removed. Main ancestry, the original stable candidate,
historical plans, and acceptance records remain intact. With the beta checkout
gone, stable packaging produced identical bytes and the extracted ZIP again
passed legacy migration, update, discovery, and repeated removal checks.
Previously downloaded or installed beta copies were not remotely removed; use
the [stable migration instructions](installation.md#return-from-retired-beta).

## Historical adaptive beta acceptance — October 13, 2026

**Retired on October 14, 2026.** The following records describe the earlier
experiment, not current features or installation instructions. Use the stable
[migration guide](installation.md#return-from-retired-beta).

At the time of this experiment, `main` held stable `0.1.0` and the separate
`beta` source prepared `0.2.0-beta.1`. These were local release candidates, not
published releases. The stable renderer and original example fixtures retained
their baseline bytes. Adaptive rendering, providers, state, and examples were
implemented only in beta.

### Automated and channel checks

| Source | Python 3.11.17 | Python 3.14.5 | Local platform |
| --- | --- | --- | --- |
| Stable | 181 passed | 181 passed | macOS 26.5.2, Apple Silicon |
| Beta | 217 passed | 217 passed | macOS 26.5.2, Apple Silicon |

Linux and Windows are configured in CI but were not executed locally for this
change. The unit suite includes mocked callback payloads, concurrent session
isolation, expired/future records, unknown profiles, failed storage, installer
rollback, later settings edits, and shared host registrations. These are
automated checks, not live acceptance of other host versions or platforms.

Subsequent CI results passed on Ubuntu and macOS but failed on both Windows
Python versions: Git converted the bundled `LICENSE` to CRLF, invalidating its
sealed byte hash. License files now explicitly use LF. A regression stages the
real bundle in Git and checks it out with `core.autocrlf=true`, verifying every
sealed file and an identical ZIP. A second Windows failure came from embedding
the runner's temporary path in Python source: `\a` became a control character.
The workflow now reads `RUNNER_TEMP` from the environment. Its regression runs
the actual distribution command with spaces and backslashes in that path.
All six stable jobs, including both Windows versions, passed after these fixes
([run](https://github.com/bao96-bioinfo/SpecViz/actions/runs/38485321472)).

The beta run then exposed Windows access errors when concurrent callbacks
replaced the same display record. Replacement now retries Windows access and
sharing errors with at most 250 milliseconds of retry delays. Persistent and
unrelated failures still propagate; the previous record remains intact and
temporary files are cleaned up. Tests cover these failure paths alongside the
existing competing-writer check. The local counts above include these fixes;
subsequent hosted results are tracked in
[Checks](https://github.com/bao96-bioinfo/SpecViz/actions/workflows/checks.yml).
The beta candidate was resealed and rebuilt reproducibly with the runtime fix;
its updated hashes are in `release-candidates.json`. The stable archive is unchanged.

The beta source's `tools/channel_acceptance.py` exercised actual extracted ZIP
installers: default stable install, rejection of a beta source without opt-in,
explicit beta install/update, shared Codex stable output, return to stable,
and repeated removal. Stable continuations and evidence database bytes survived;
beta-only tokens requested a fresh stable view. Custom files and unrelated
settings remained intact. Reproduce from the beta checkout:

```sh
python3 tools/channel_acceptance.py \
  --stable-source /path/to/SpecViz \
  --beta-source /path/to/SpecViz-beta
```

This explicit maintainer check temporarily registers its isolated test project
with Antigravity's user dispatcher and unregisters it in cleanup. It does not
launch an agent or execute project source.

### Actual interactive terminal checks

Both installed skills ran ordinary `/specviz overview` requests in interactive
terminal sessions, using the eight-file training fixture and its supplied,
source-backed interpretation. The agent received its session binding from the
installed hook. No width option or width question was used. Terminal dimensions
were changed by the test harness; the product read real host callbacks.

| Host and rendering mode | Terminal columns | Content columns | Observed result |
| --- | --- | --- | --- |
| Claude Code 2.1.296, default | 48 | 44 | Closed single-column panels and complete sentences fit |
| Claude Code 2.1.296, default | 160 | 156 | Parallel branches and an outside connector fit; detailed `show 1` also fit |
| Antigravity 1.3.3, default/local terminal | 48 | 38 | Two-part overview; first-part boxes and long file keys fit the code block |
| Antigravity 1.3.3, default/local terminal | 120 | 110 | Full overview fits with parallel branches |
| Antigravity 1.3.3, default/local terminal | 160 | 150 | Wider boxes reduce wrapping; the multi-stage flow remains vertical |

Both hosts were widened and narrowed after idle. Subsequent ordinary requests
used fresh, session-matched host measurements. Initial requests at 120 columns
with profiles disabled used the expected 78-column fallback. Their success
did not count as measured-width acceptance.

Calibration caught an Antigravity failure: subtracting only the visible
four-column left indent left a long path rewrapped by the host. Accounting for
eight columns of code-block padding corrected the 48-column case; 120- and
160-column checks then passed. Only the verified profiles are enabled. Other
versions/modes remain on fallback. A five-second expiry and one-second maximum
wait limit stale observations, but cannot detect an unreported resize between
callback and display. Concurrent/resumed binding was checked automatically;
multiple interactive sessions of the same host were not claimed as a live test.

These were terminal sessions, not `--print` runs or desktop/editor previews.
The beta's optional `tools/terminal_acceptance.py` drives a real terminal through
`pyte`; it is not part of CI or a runtime dependency. For future acceptance,
install beta into an isolated project, request an overview at narrow and wide
sizes, resize while idle, and inspect the final chat text as well as the saved
presentation's `display` record. Do not enable a profile solely from a helper
golden test. Temporary registrations and project trust were removed; original
Antigravity settings were restored byte-for-byte. Specification hashes remained
unchanged. Private host transcripts and account information are not checked in.

### Direct output and layout review

The actual beta helper also wrote directly to an attached pseudo-terminal at
48, 80, 120, and 160 columns, without `--width` or display-context arguments.
All twelve runs reported `terminal` provenance and reserved two columns:

- A three-stage report-download flow was vertical at 48/80 and horizontal at
  120/160, preserving both labeled arrows.
- Sixteen independent report formats used aligned rows; the wide view had four
  columns and four rows without invented arrows.
- The eight-file example used named panels when narrow, then connected branches
  and vertical stages as more space became available.

The rendered text was reviewed for reading order, complete explanations,
closed borders, useful spacing, and file-key fit. Separately, 40 maintained
beta examples cover both detail levels, five frameworks, and both comparison
evidence modes. Their golden tests preserve logical content across widths;
they do not establish the quality of an arbitrary agent interpretation.

At that time, Codex adaptive support was **under development**; that effort is now retired. Its stable renderer was
checked through a shared beta installation; no Codex width provider is claimed.
Desktop/editor measurement and marketplace installation remain untested.

## Automated checks

For the maintained stable source, run from the repository root:

```sh
python3 -m unittest discover -s tests -v
openspec validate --all --strict
git diff --check
```

The standard-library suite checks discovery for all five frameworks, source
coverage, four text layouts, both detail levels, scoped comparison, immutable
evidence, inspection freshness, installation, and maintained examples. The
GitHub workflow configures Linux, macOS, and Windows with Python 3.11 and 3.14.
Local execution does not establish that the other operating systems have run.

## Live host procedure

From the stable checkout, `tools/host_acceptance.py` installs the maintained skill into five isolated
projects, supplies source-backed interpretation models, and uses an external
shared state directory. Reports are explicitly fictional test inputs; their
verification is unavailable. Each project contains a four-line export function
with an owner check and row limit, without password encryption.

```sh
python3 tools/host_acceptance.py --prepare-only
python3 tools/host_acceptance.py --host codex --workspace <printed-directory>
python3 tools/host_acceptance.py --host claude-code --workspace <same-directory>
python3 tools/host_acceptance.py --host antigravity --workspace <same-directory>
```

For smaller sessions, add `--framework openspec` (or another framework name).
`--effort low` selects reasoning effort for that test session only. Run all five
cases before recording complete framework coverage.

Antigravity headless command approval may require an explicit permission rule.
The optional `--headless-auto-approve` flag is for a fully trusted isolated test
workspace; it does not change global settings. See the
[official headless permission documentation](https://www.antigravity.google/docs/cli/headless/).

Inspect actual command exits, source snapshots, views, evidence receipts, and
findings. A runner timeout or a host's assertion is not a pass. Raw transcripts
and temporary interpretations remain in the printed workspace, outside Git.
These checks exercise host integration with supplied models, rather than
proving that an agent can interpret every specification correctly.

## Recorded live results

The October 12 native runs exercised the pre-change installed bundle. Each host invoked
a fixed fixture driver using supplied interpretations and previously reviewed,
agent-authored observational findings. The driver executed 14 commands per
framework, including whole/local views, numbered selection, both detail levels,
report and inspection views, duplicate handoff import, and ready-artifact
overview. Each host then printed an actual diagram in its final chat response.

| Framework | Codex | Claude Code | Antigravity |
| --- | --- | --- | --- |
| OpenSpec | Passed | Passed | Passed |
| GitHub Spec Kit | Passed | Passed | Passed |
| BMAD Method | Passed | Passed | Passed |
| Superpowers | Passed | Passed | Passed |
| Kiro Specs | Passed | Passed | Passed |

| Tested surface | Observed version | Final run |
| --- | --- | --- |
| `codex exec` | 0.162.1 | 70 successful helper commands; 26.44 seconds |
| `claude --print` | 2.1.296 | 70 successful helper commands; 16.50 seconds |
| `agy --print` | Installed terminal build; version not reported | 70 successful helper commands; 18.35 seconds |

Final sessions used `--effort low`, or Codex's session-only equivalent. The
Antigravity run used explicit tool approval for the trusted fixture workspace.
Native graphical application and IDE surfaces were not exercised.

All installed bundle files matched maintained source, all original specification
and application hashes remained unchanged, and each project retained exactly
one fictional completion event. Claude Code and Antigravity successfully reused
the same external checkout evidence as Codex. Inspections remained separate;
no verification execution was fabricated.

Earlier large-agent requests timed out, and Antigravity's initial headless run
denied a command permission. A subsequent harness failure replayed a stored
receipt containing derived metadata instead of its original handoff. Restoring
the raw input reproduced its original delivery hash and resolved the conflict
without changing evidence history. These attempts were not counted as passes.
The final scoped runs completed with zero exits and native text responses.

## Interpretation and reader review

A fresh agent received the comparison project's original Markdown, application,
and test definitions without expected diagrams. It generated and validated its
own interpretation, used stable numbered selection, and kept checked tasks
separate from completion evidence. Its first review found duplicated task text
caused by a combined list block. Per-item source blocks and a regression check
correct that issue.

Its requested code inspection then traced application behavior and existing test
definitions without running them. It correctly treated a returned filename as
partial evidence for file creation and found the password path contradictory.
The maintained inspection example was corrected to preserve that distinction.

A second raw inspection fixture exercised cross-module tracing and all five
findings. The agent followed `service.py` into `exporter.py` and the externally
supplied storage adapter:

| Requested behavior | Observed finding and limit |
| --- | --- |
| Owner check and 100-row limit | Supported in `exporter.py:1-4`; execution unverified |
| Downloadable file | Partial: bounded rows returned; file creation/delivery unestablished |
| Password encryption | Contradicted: supplied password is ignored by the exporter |
| Administrator audit view | Not found in the fully read local service modules; external behavior uninspected |
| Storage encryption at rest | Unclear: `service.py:6` delegates to an unavailable external adapter |

The helper accepted version-bound findings and printed the actual comparison.
Source/task hashes remained unchanged; reading test definitions did not become
passing verification. Inputs are under `tests/fixtures/inspection/project/`.

A separate fresh reader reviewed the Kiro overview and report-based comparison
from text alone. It identified report downloads, the requirements/design/tasks
roles, changed password protection, affected design and tasks, and unavailable
verification. Its feedback led to clearer earlier-behavior labels, arrow
explanations, snapshot captions, and follow-up commands.

The project author also reviewed the compact hierarchical change prototype and
answered **“Clear enough.”** This is a small qualitative review, not a usability
study. [Interpretation cases](interpretation-review.md) explain how contributors
should check meaning preservation beyond deterministic source coverage.

## Diagram-first response review

Use `tests/fixtures/diagram-first/project/` and an installed current skill. Read
raw source rather than supplying an expected answer. Request an overview, then
`show` for the design file in both detail levels. Check the final chat response,
not just helper output, against [the interpretation rubric](interpretation-review.md).

| Request or context | Required observation |
| --- | --- |
| Ordinary overview | Project purpose, connected boxes, compact file keys, at most one selection hint |
| Prior conversation contains code changes | No unsolicited drift report, implementation inspection, or offer to edit specs |
| Meaningful connector labels already present | No second edge list or prose retelling |
| Unknown term or unavailable source | Uncertainty stays visible beside its claim or in a keyed warning |
| `show <file>` then `--detailed` | Same logical nodes and edges; full source conditions and unresolved decisions retained |
| `changes` | Reports only; missing evidence remains unknown |
| `changes --check-code` | Separate source-backed observations; no fabricated test execution or completion |
| Paged file key | Continue with the same session; unopened file numbers are rejected |

An opaque box or a fluent unsupported explanation fails this review even when
model validation and golden-output tests pass. Previous host results above
apply to their recorded bundle, not automatically to this presentation change.

## Diagram-first implementation checks — October 13, 2026

The complete 163-test suite passes locally on macOS 26.5.2 (Apple Silicon) with
Python 3.14.5 and 3.11.17. It covers boxed branches and joins, source-backed
project interpretations, legacy models, all comparison evidence states,
12-line continuation pages, long keys, per-conversation delivered selections,
legacy saved pages, and persistence failures. The original five framework
fixture hashes and comparison inputs are unchanged.

Linux and Windows runs for this change are **not yet verified**. The maintained
GitHub Actions matrix remains Python 3.11/3.14 on all three operating systems.
The local Python checks do not substitute for those pending platform runs.

The ZIP was rebuilt with `tools/package.py` and compared byte-for-byte with
every maintained bundle file, including `layout.py`, `views.py`, `text.py`, and
`pagination.py`. `tools/host_acceptance.py --prepare-only` installed that bundle
into five isolated framework projects. All 15 combinations of three agent
installation paths and five fixture overviews ran successfully through the
installed helper. Project and installed-bundle hashes remained unchanged.
These are packaging/helper checks, not fresh Claude Code or Antigravity chats.

### Current conversation and reader preview

The current Codex assistant used an isolated, installed SpecViz skill to read
the eight-file fixture, validate its source-backed interpretation, and run the
installed helper for overview, `show 1`, and `show 1 --detailed`. The local desktop
bundle reports ChatGPT 26.1007.30912 (build 20156); Python was 3.14.5. This was an
interactive tool-driven conversation, not a new `codex exec` run or a test of
native command discovery. Fresh Claude Code and Antigravity conversations for
this change remain **unverified**.

The overview and file views retained six logical compartments, the training
branch, separately held answers, their evaluation join, and all eight source
files. Detailed design notes preserved the all-checks-pass condition, the
stop-and-report outcome, hidden evaluation answers, repeated settings, and the
prohibition on declaring readiness with an undecided threshold. The comparison
and source-integrity checks remain separate from this explanation review.

The review improved the training annotation to name input loading, a short run,
and saving results; it also made “do not declare the model ready” explicit in
the overview. An initial selected-file attempt reused the global project graph
and correctly failed out-of-scope reference validation. The skill and contract
now explicitly use document models for `show`/`changes` and scope-specific
project graphs for overviews. Both selected-file requests then passed. No
specification hash changed and no implementation-evidence database was created.

The complete 80-line overview was printed in the conversation for a reader
check. The project author replied **“It's much clearer.”** They asked about
future console-width detection and horizontal layouts, explicitly requesting
no modification for now. This is qualitative reader feedback, not an
independent comprehension study. Width behavior remains unchanged. The maintained source and all
three generated view forms are reproducible in
[the eight-file example](../examples/diagram-first/README.md).

### Requirement coverage

| Requirement group | Delivered behavior and verification |
| --- | --- |
| Project/document purpose; connected boxes | `views.py` uses the project graph and compact file key; eight-file overview and legacy fallback tests in `test_diagram_views.py` |
| Stable detail; appropriate visual form | Box/edge identities remain stable; hierarchy, flow, interactions, independent rules, branches, joins, and cycles in `test_layout.py` and `test_render.py` |
| Understandable labels; useful annotations | Skill asks for meaningful titles and supported sentences; source review and negative cases in `interpretation-review.md` |
| Large/narrow views; traceability | Measured wrapping, counted groups, keyed panels, complete source keys, and 12-line pages in `test_pagination.py`; selection and stale-source rejection in `test_cli.py` |
| Grounded project explanation; older models | Additive version-one contract, source/scope/coverage validation, and boxed fallback in `test_core.py` and `test_diagram_views.py` |
| Comparison evidence distinctions | Adjacent evidence limits and group/file/behavior markers; unchanged comparison engine, renderer tests, and both maintained comparison modes |
| Approachable entry point; representative examples | README embeds actual Kiro output; five framework examples, eight-file branch/join, and both comparison modes reproduce from checked source bytes |
| No duplicate explanation; requested-mode boundary | Installed skill instructions and response-review cases above; current conversation printed the generated overview without drift claims |
| Understanding checked against source | All eight source files reviewed against concise/detailed output; reader feedback requested separately from automated results |

Strict OpenSpec validation passes all eight items. `git diff --check` passes.
The pre-existing `AGENTS.md` hash is unchanged. Visualization preserved the
original source fixtures, report/inspection inputs, and evidence semantics;
OpenSpec baseline synchronization and task tracking were explicit workflow work.
