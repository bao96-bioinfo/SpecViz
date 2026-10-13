# Workflow handoffs

SpecViz supports explicit source-bound handoffs for OpenSpec, GitHub Spec Kit,
BMAD Method, Superpowers, and Kiro Specs. It cannot infer completion from a
command invocation, task checkbox, archival action, or branch merge.

Use the installed `scripts/specviz_cli.py` path. Before a workflow begins actual
implementation, choose a persistent round identity and capture its selected
specification versions:

```sh
python3 <skill>/scripts/specviz_cli.py overview <feature-folder> \
  --project <project> --capture-round <round> --framework openspec \
  --host codex --json
```

On pause/resume, retain that round and scope. If sources change during the
round, explicitly bind coverage to the version actually implemented. Completion
and progress records follow [evidence.md](evidence.md); import with `--event`.
The returned begin receipt retains the original specification text and hashes.
Use `comparison.requested_text(item, document)` for exact covered source text.
Fingerprint relevant current code with `evidence.implementation_identity`.

| Workflow | Evidence-bearing handoff point |
| --- | --- |
| OpenSpec | Apply begins; progress or declared task scope completes; verification report arrives. Sync/archive are document lifecycle events. |
| GitHub Spec Kit | Implementation phase begins; phase progress or declared scope completion; verification/convergence results arrive. |
| BMAD Method | Build begins; built work is progress; explicit done/completion closes the declared scope; verification is separate. |
| Superpowers | Plan execution begins; task progress; final execution/finishing report for the declared scope; review/test results are separate. |
| Kiro Specs | Selected task execution begins; partial task progress or selected scope completion; verification is separate. |

For persisted explicit reports, use `*.specviz-report.json` beside the discovered
specification documents, or pass their paths with `--reports`. These are inputs,
not generated checkpoints; SpecViz retains its own state outside the project.
Unsupported native formats are reported without converting checkboxes into
compliance. Record actual originating reports, not invented verification.

## Ready specifications

Install with `--generation-handoff` to enable explicit ready-artifact handoffs.
When a generating workflow actually invokes SpecViz with ready artifacts, run:

```sh
python3 <skill>/scripts/specviz_cli.py overview --project <project> \
  --generation-ready <generated-group> --json
```

Then interpret and render the full overview with the same flag and a validated
model. This marks current work without narrowing the project overview or
starting implementation. Disabled handoffs return their disabled status.
The setting alone does not install an untested host lifecycle hook; use the
explicit generating agent handoff above. Native automatic hooks are separately
listed in the compatibility matrix.
