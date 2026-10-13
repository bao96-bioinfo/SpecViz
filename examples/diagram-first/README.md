# Eight files, one understandable workflow

This synthetic training workspace shows how a larger specification becomes
connected text boxes. The diagram follows training samples through prediction,
keeps evaluation answers separate, then joins them to measure prediction error.
It also keeps the undecided acceptance threshold visible.

The source is `tests/fixtures/diagram-first/project/`. Its OpenSpec change contains
a proposal, design, task checklist, and five capability specifications.
`model.json` records the reviewed interpretation, and `selection.json` selects
the design. Tests verify the fixture's exact bytes before rebinding its snapshot
to a different checkout. No source or data from a private scientific project is
included.

Run `python3 -m unittest discover -s tests -p 'test_diagram*.py' -v` from the
repository root to check the example and its generated views.

| View | Concise | Detailed |
| --- | --- | --- |
| Project overview | [Diagram](overview.txt) | [Expanded](overview-detailed.txt) |
| Design file | [Diagram](show.txt) | [Expanded](show-detailed.txt) |

In this fixture, `show 1` selects `design.md` after its file key is delivered.
`show openspec/changes/reproducible-model-training/design.md --detailed` selects
the same file by exact path.
