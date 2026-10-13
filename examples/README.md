# Text examples

The five framework projects describe a reporting service with a data export feature. The examples demonstrate text returned in the conversation; their files make the expected output reviewable during development.

| Framework | Overview and selected-file examples | Source fixtures |
| --- | --- | --- |
| OpenSpec | [OpenSpec](openspec/README.md) | [Project](../tests/fixtures/frameworks/openspec/project) |
| GitHub Spec Kit | [Spec Kit](spec-kit/README.md) | [Project](../tests/fixtures/frameworks/spec-kit/project) |
| BMAD Method | [BMAD](bmad/README.md) | [Project](../tests/fixtures/frameworks/bmad/project) |
| Superpowers | [Superpowers](superpowers/README.md) | [Project](../tests/fixtures/frameworks/superpowers/project) |
| Kiro Specs | [Kiro](kiro/README.md) | [Project](../tests/fixtures/frameworks/kiro/project) |

Start with `overview`, then use `show <file>`. Add `--detailed` to either command to expand annotations without changing the file identities or diagram order. Each example has a source-backed interpretation model and expected output for both levels. The full model remains a development artifact; users normally ask their coding agent to interpret the specifications.

The examples demonstrate helper behavior against pinned source layouts. They do not establish successful invocation in every coding application; see the [compatibility matrix](../docs/compatibility.md) for tested surfaces and limitations.

## A larger connected diagram

The [eight-file training example](diagram-first/README.md) includes two branches,
a join, five files named `spec.md`, and source-defined specialist terms rewritten
as clear sentences. [Compare reports and code findings](comparison/README.md)
for both evidence modes.

## Reproduce the examples

Run `python3 -m unittest discover -s tests -p test_examples.py -v` from the
repository root. The test copies each fixture to a temporary project, checks
all source and configuration files against the reviewed
[content hashes](../tests/fixtures/frameworks/content-hashes.json), and renders
both detail levels. Snapshot identifiers depend on the checkout location;
only that caption is adjusted when comparing with the saved examples.

When changing a fixture, review its interpretation and all four expected views
before updating the content hashes. A changed requirement must not be accepted
solely by refreshing its snapshot identifier.
