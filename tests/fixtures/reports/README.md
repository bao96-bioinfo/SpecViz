# Explicit report handoff fixtures

These fixtures are synthetic **SpecViz evidence schema 1** events. Each embeds
its actual handoff-contract version and an upstream workflow source URL. They do
not assert support for native persisted report formats or universal hooks.

| Fixture | What it exercises |
| --- | --- |
| `openspec.json` | Scope completion with retained specification text |
| `spec-kit.json` | Phased implementation progress |
| `bmad.json` | Built work that remains progress |
| `superpowers.json` | Captured execution completion, independent of later workspace removal |
| `kiro.json` | Partial task execution with a requirement-version binding |

The implementation code fingerprints are deliberately unavailable in these
portable fixtures. They illustrate record provenance, not current compliance
with an unrelated checkout. Executable tests bind fresh code fingerprints in
isolated projects to exercise applicable evidence, drift, and concurrency.
