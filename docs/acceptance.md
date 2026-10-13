# Acceptance checks

Checks recorded on October 12, 2026. Automated fixtures, live coding hosts,
language interpretation, and reader feedback are separate evidence.

## Automated checks

Run from the repository root:

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

`tools/host_acceptance.py` installs the maintained skill into five isolated
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

The final native runs exercised the current installed bundle. Each host invoked
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
