# Compatibility

Support is recorded separately for file discovery, installation, live invocation,
workflow evidence, generation handoffs, and code inspection. Passing a fixture test
establishes the helper's local behavior for that layout; it does not establish that
a particular coding host has executed the skill successfully.

## Framework discovery

All five readers have executable tests in `tests/test_discovery.py`. The examples
under `tests/fixtures/frameworks/` contain original illustrative text. Their
`provenance.json` files pin the primary upstream sources inspected on October 12,
2026. Support covers these mappings rather than every historical framework version.

| Framework | Tested file mapping | Pinned source |
| --- | --- | --- |
| OpenSpec | `openspec/specs/**`, active `changes/<name>/**`, and dated `changes/archive/**`; main specifications, deltas, proposals, design, and tasks retain separate roles. The default `spec-driven` workflow branches from proposal to specifications and design, then tasks. | [Schema at 9111a765](https://github.com/Fission-AI/OpenSpec/blob/9111a7654d7800391459431fff4eaf66e33a3d2e/schemas/spec-driven/schema.yaml) |
| GitHub Spec Kit | `specs/<feature>/{spec,plan,tasks}.md`, research, data model, quickstart, contracts, and `.specify/memory/constitution.md`. `.specify/feature.json` and `SPECIFY_FEATURE_DIRECTORY` add configured feature roots; neither hides other features from a global overview. | [Core reference at 6c62e10d](https://github.com/github/spec-kit/blob/6c62e10d5ab1d676c557eb2d0cee86be52c893d2/docs/reference/core.md) |
| BMAD Method | Default `_bmad-output` or layered `_bmad/{config.toml,custom/config.toml,custom/config.user.toml}` using `[core].output_folder`. Initiative and epic trees contain briefs, specifications, `tickets.toml`, and story plans. All initiatives remain visible. `status: built` is displayed as a reported status, with implementation evidence still unknown. | [Ticket tree at 9f198716](https://github.com/bmad-code-org/BMAD-METHOD/blob/9f1987169a2e5626e5ccb31bb9cee051fdb3df20/docs/plan/set-up-the-ticket-tree.md) |
| Superpowers | `docs/superpowers/specs/*.md` and `plans/*.md`; a plain or bold `Spec:` field can identify an agreed alternative design location inside the project, including quoted paths. Explicit references determine relationships. | [Writing plans at bb92a777](https://github.com/obra/superpowers/blob/bb92a77741419a4ab5f06e711a283343f1ada0c3/skills/writing-plans/SKILL.md) |
| Kiro Specs | `.kiro/specs/<feature>/{requirements,bugfix,design,tasks}.md`. The limited observed `.config.kiro` fields `workflowType` and `specId` distinguish requirements-first and design-first. Missing workflow metadata leaves document order unspecified; incomplete feature directories remain visible. | [IDE 0.12](https://kiro.dev/changelog/ide/0-12/), [feature workflows](https://kiro.dev/docs/specs/feature-specs/), [observed metadata](https://github.com/kirodotdev/Kiro/issues/9435) |

## Roots and discovery limits

An explicit project directory takes precedence. Otherwise, discovery resolves the
nearest repository or framework boundary; `SPECIFY_INIT_DIR` can explicitly select
a Spec Kit project. Starting inside a change or feature never narrows a global
overview to that feature. `overview <folder>` and selected file views retain direct
references outside their analysis scope as labeled context.

OpenSpec top-level `schema`, scalar `store`, and scalar-list `references` are read
without evaluating YAML. If stores are declared and OpenSpec is installed, the
read-only `openspec store list --json` registry resolves their `root` locations.
As in OpenSpec, an existing local `specs/` or `changes/` directory takes precedence
over a `store:` declaration; use `references:` to include read-only store context.
Unavailable stores remain explicit discovery warnings. Inline YAML reference
objects, aliases, tags, and other unsupported relevant constructs are reported.
Custom schemas retain documents without invented workflow dependencies. BMAD
legacy YAML configuration is reported as unsupported; select its actual planning
folder explicitly for a generic view. Current TOML parsing never executes code.

Automatic discovery excludes installed agent skills, dependency directories,
version-control internals, caches, and build output. External symlinks are not
opened without a declared root or explicit selection. Directory symlinks are
reported and require explicit selection; this avoids recursive loops. Configured
external roots use full `external::` source identities and unavailable roots remain
visible as incomplete discovery.

Explicit unfamiliar Markdown files receive generic section views and unknown
framework behavior. Markdown references inside the project may add supporting
documents as context. Missing references preserve the referring source line;
cycles remain cycles. Unsupported text, invalid encoding, and unreadable paths
produce warnings rather than disappearing from a claim of complete discovery.

Discovery alone records no implementation completion, verification, or code
inspection. Archiving, synchronizing, checking a task, or finding a file cannot
establish that the corresponding behavior was implemented.

## Workflow evidence and inspection

The executable evidence fixtures exercise **SpecViz handoff schema 1**, identified
as captured reports in `origin.kind: handoff`. The source URLs in those fixtures
describe each upstream workflow; the fixture is not a claim that upstream emits
this format natively. The persisted `*.specviz-report.json` convention is a
SpecViz handoff that `changes` can import, not a native framework report.

| Framework | Tested explicit handoff | Native report / automatic lifecycle capture |
| --- | --- | --- |
| OpenSpec | Begin/resume, per-requirement progress, declared apply-scope completion, separate verification | Unsupported; synchronization and archival do not imply completion |
| GitHub Spec Kit | Scoped phased progress, completion, verification with retained source versions | Unsupported; checked tasks alone remain progress |
| BMAD Method | Build progress and explicit completed scope; verification remains separate | Unsupported; `built` cannot close a round |
| Superpowers | Captured execution/completion and verification; retained evidence survives temporary workspace removal | Unsupported; command names do not create reports |
| Kiro Specs | Partial task/requirement progress and declared scope completion | Unsupported; task status without version bindings does not establish compliance |

Optional code inspection is independent of the originating framework once its
requirements have been mapped to source items. Fixture-tested findings are
observational and include source locations, code fingerprints, and uninspected
portions. Tests are not executed. Cached findings are reused only when their
source versions still match. Live agent inspection and lifecycle capabilities
require separate host acceptance; helper fixture success is not a substitute.

Declared external specification roots support discovery, text views, and
retained workflow reports. Persisted code-inspection findings for `external::`
sources and external implementation fingerprints are currently unsupported;
requests disclose this limitation. Specification files in configured local
roots are excluded from code-drift checks, including non-Markdown artifacts.

See [comparison meanings](comparison.md) and the [evidence contract](../skills/specviz/references/evidence.md).

## Coding hosts

Project-scoped installation, update, removal, shared invocation semantics, and
the five-framework acceptance pipeline have been checked on these terminal
surfaces. Detailed results and test limits are in [acceptance](acceptance.md).

| Host | Tested surface | Skill location | Invocation |
| --- | --- | --- | --- |
| Codex 0.162.1 | `codex exec` | `.agents/skills/specviz/` | `$specviz` |
| Claude Code 2.1.296 | `claude --print` | `.claude/skills/specviz/` | `/specviz` |
| Antigravity installed build | `agy --print`, with explicit headless tool approval | `.agents/skills/specviz/` | `/specviz` |

Each exercised global/local overview, numbered file selection, both detail
levels, workflow handoff comparison, and explicit code inspection. Reports and
inspections stayed usable across hosts in the same checkout. Explicit
ready-artifact callbacks worked; no native automatic lifecycle observer is
advertised. Interactive IDE surfaces and other host versions remain untested.
