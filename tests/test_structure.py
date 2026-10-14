"""Check drawn connectors, bounded expansion, and map-before-panel delivery."""

import random
import unittest
from large_project_fixture import load_fixture
from specviz.layout import Box, Edge, Graph, View
from specviz.structure import MapBlock, _row, _lanes, _spine, compact_maps
from specviz.pagination import paginate
from specviz.text import display_width
from specviz.views import overview_view, show_view, changes_view


def follow(grid, start, arrows):
    """Trace actual glyphs: x continues straight, and only + may turn."""
    queue = [start]
    seen = set()
    found = set()
    while queue:
        x, y, dx, dy = queue.pop()
        if (x, y, dx, dy) in seen:
            continue
        seen.add((x, y, dx, dy))
        if not 0 <= y < len(grid) or not 0 <= x < len(grid[y]):
            continue
        if (x, y) in arrows:
            if (grid[y][x], dx, dy) in {
                ("v", 0, 1),
                ("<", -1, 0),
                (">", 1, 0),
                ("^", 0, -1),
            }:
                found.add(arrows[x, y])
            continue
        char = grid[y][x]
        if char == "-" and dy or char == "|" and dx:
            continue
        choices = (
            [(dx, dy)]
            if char == "x"
            else [(1, 0), (-1, 0)]
            if char == "-"
            else [(0, 1), (0, -1)]
            if char == "|"
            else [(1, 0), (-1, 0), (0, 1), (0, -1)]
            if char == "+"
            else []
        )
        for a, b in choices:
            if (a, b) != (-dx, -dy):
                queue.append((x + a, y + b, a, b))
    return found


class StructureTests(unittest.TestCase):
    def graph(self, n=7, relations=None):
        relations = (
            relations
            if relations is not None
            else [(0, 1), (0, 3), (2, 1), (1, 3), (3, 4), (4, 6), (5, 6), (1, 6)]
        )
        return Graph(
            [
                Box(str(i), f"Component {i + 1}", ["Explanation. " * 60])
                for i in range(n)
            ],
            [
                Edge(str(a), str(b), f"Condition {i}", "condition", i % 2 == 0)
                for i, (a, b) in enumerate(relations)
            ],
        )

    def assert_routes(self, edges, n):
        labels = [f"Node {i}" for i in range(1, n + 1)]
        for renderer in (_row, _lanes):
            grid = renderer(labels, edges, 160)
            self.assertIsNotNone(grid)
            starts = []
            arrows = {}
            if renderer is _row:
                size = max(map(len, labels)) + 2
                top = 2 * len(edges) + 1 if edges else 0
                for node in range(n):
                    attached = [
                        (i, side)
                        for i, (a, b) in enumerate(edges)
                        for side, endpoint in [("out", a), ("in", b)]
                        if endpoint == node
                    ]
                    for offset, (i, side) in enumerate(attached, 1):
                        x = node * (size + 3) + offset
                        if side == "out":
                            starts.append((i, (x, top - 1, 0, -1)))
                        else:
                            arrows[x, top - 1] = node
            else:
                size = max(map(len, labels)) + 4
                top = 0
                for node in range(n):
                    attached = [
                        (i, side)
                        for i, (a, b) in enumerate(edges)
                        for side, endpoint in [("out", a), ("in", b)]
                        if endpoint == node
                    ]
                    for offset, (i, side) in enumerate(attached, 2):
                        if side == "out":
                            starts.append((i, (size, top + offset, 1, 0)))
                        else:
                            arrows[size, top + offset] = node
                    top += 4 + len(attached)
            for i, start in starts:
                self.assertEqual(
                    follow(grid, start, arrows), {edges[i][1]}, "\n".join(grid)
                )

    def test_drawn_fixture_branches_joins_and_long_edges_have_no_false_junctions(self):
        self.assert_routes(
            [(0, 1), (0, 3), (2, 1), (1, 3), (3, 4), (4, 6), (5, 6), (1, 6)], 7
        )
        self.assert_routes(
            [(0, 1), (0, 2), (0, 3), (1, 4), (2, 4), (3, 4), (4, 0), (2, 2)], 5
        )

    def test_backbone_glyphs_draw_exactly_the_source_edges(self):
        import re

        relations = [(0, 1), (0, 3), (2, 1), (1, 3), (3, 4), (4, 6), (5, 6), (1, 6)]
        grid = _spine([f"Node {i}" for i in range(1, 8)], relations, 80)
        self.assertIsNotNone(grid)
        arrows = {}
        starts = []

        def inspect(node, x, y, dx, dy):
            if not 0 <= y < len(grid) or not 0 <= x < len(grid[y]):
                return
            char = grid[y][x]
            if char in "<>^v":
                arrows[x, y] = node
            elif char == ("|" if dy else "-"):
                starts.append((node, (x, y, dx, dy)))

        for row, line in enumerate(grid):
            for match in re.finditer(r"\| Node (\d+) +\|", line):
                node = int(match[1]) - 1
                left, right = match.start(), match.end() - 1
                inspect(node, left - 1, row, -1, 0)
                inspect(node, right + 1, row, 1, 0)
                for x in range(left + 1, right):
                    inspect(node, x, row - 2, 0, -1)
                    inspect(node, x, row + 2, 0, 1)
        observed = set()
        for node, start in starts:
            observed.update((node, target) for target in follow(grid, start, arrows))
        self.assertEqual(observed, set(relations))

    def test_large_fixture_map_and_all_short_keys_are_on_page_one(self):
        inv, model = load_fixture()
        for detailed in (False, True):
            view = overview_view(inv, model, detailed)
            page = paginate(view)[0].text
            self.assertIn("Specification map (10 files)", page)
            self.assertNotIn("archive/", page)
            for n in range(1, 8):
                self.assertIn(f"Node {n}:", page)
            graph = next(b for b in view.blocks if isinstance(b, Graph))
            units = graph.presentation(80)
            root = next(b for b in units if isinstance(b, MapBlock))
            self.assertEqual(set(root.edges), set(range(1, 9)))
            self.assertIn("\n".join(root.lines), page)
            self.assertLess(page.index("| Node 1 |"), page.index("Component details"))
            self.assertEqual(page.count("Node 7: Assemble the notebook"), 1)
            self.assertEqual(
                [b.identity for b in graph.panels()], [b.identity for b in graph.boxes]
            )

    def test_dense_disconnected_feedback_and_minimum_budgets_terminate_with_complete_maps(
        self,
    ):
        cases = [
            (40, [(a, b) for a in range(40) for b in range(40) if a != b]),
            (51, [(i, i + 1) for i in range(0, 48, 3)]),
            (3, [(0, 0), (1, 2), (2, 1)]),
        ]
        for n, relations in cases:
            graph = self.graph(n, relations)
            for width, budget in [(24, 8), (80, 96)]:
                units, keys = compact_maps(graph, width, budget)
                maps = [b for b in units if isinstance(b, MapBlock)]
                self.assertEqual(set().union(*(set(b.nodes) for b in maps)), set(keys))
                self.assertEqual(
                    set().union(*(set(b.edges) for b in maps)),
                    set(range(1, len(relations) + 1)),
                )
                self.assertLessEqual(len(maps), 4 * n + 2 * len(relations))
                self.assertEqual(compact_maps(graph, width, budget), (units, keys))
                for b in maps:
                    self.assertLessEqual(len(b.lines), budget)
                    self.assertTrue(
                        all(display_width(line) <= width for line in b.lines)
                    )
                self.assertIsInstance(units[0], MapBlock)

    def test_overview_show_changes_and_direct_output_share_structural_units(self):
        inv, model = load_fixture()
        for view in (
            overview_view(inv, model),
            show_view(inv, model=model, detailed=True),
            changes_view(inv, {"rows": []}, model),
        ):
            direct = view.render()
            pages = paginate(view)
            for block in view.presentation():
                if isinstance(block, MapBlock):
                    geometry = "\n".join(block.lines)
                    self.assertIn(geometry, direct)
                    self.assertTrue(any(geometry in p.text for p in pages))
        view = View(24, [self.graph()])
        pages = paginate(view, 12)
        for block in view.presentation(8):
            if isinstance(block, MapBlock):
                self.assertTrue(any("\n".join(block.lines) in p.text for p in pages))
        text = "\n".join(p.text for p in pages)
        self.assertLess(
            " ".join(text.split()).index("Overall structure"),
            " ".join(text.split()).index("Component details"),
        )
        self.assertIn("Boundary", text)
        for p in pages:
            self.assertLessEqual(len(p.text.splitlines()), 12)
            self.assertTrue(
                all(display_width(line) <= 24 for line in p.text.splitlines())
            )

    def test_continued_file_graphs_keep_distinct_diagram_namespaces(self):
        first = self.graph(3, [(0, 1), (1, 2), (2, 0)])
        second = self.graph(3, [(0, 2), (2, 1), (1, 0)])
        pages = paginate(View(30, [first, second]), 12)
        text = "\n".join(p.text for p in pages)
        self.assertIn("Diagram 1, Node 2", text)
        self.assertIn("Diagram 2, Node 2", text)
        self.assertIn("Next: Diagram 2", text)
        self.assertFalse(any(p.documents for p in pages))
        for page in pages:
            self.assertLessEqual(len(page.text.splitlines()), 12)

    def test_saved_keys_are_conversation_bound_and_old_stable_pages_keep_their_text(
        self,
    ):
        import tempfile
        from pathlib import Path
        from specviz.session import ViewStore
        from specviz.core import ValidationError

        inv, model = load_fixture()
        pages = paginate(overview_view(inv, model))
        with tempfile.TemporaryDirectory() as temporary:
            store = ViewStore(Path(inv["project"]["root"]), Path(temporary))
            token = store.save(
                inv, [p.text for p in pages], "reader", [p.documents for p in pages]
            )
            original = store.load(token)
            self.assertIn("Node 2:", pages[0].text)
            with self.assertRaisesRegex(ValidationError, "not been exposed"):
                store.select(["2"], "reader")
            with self.assertRaisesRegex(ValidationError, "another conversation"):
                store.deliver(token, 2, "someone-else")
            for number in range(2, len(pages) + 1):
                store.deliver(token, number, "reader")
            self.assertEqual(store.select(["2"], "reader"), [inv["documents"][1]["id"]])
            self.assertEqual(store.load(token)["sources"], original["sources"])
            self.assertEqual(store.load(token)["pages"], original["pages"])
            legacy = store.save(inv, ["Original stable page: [1] stays [1]."])
            self.assertEqual(
                store.load(legacy)["pages"], ["Original stable page: [1] stays [1]."]
            )

    def test_unavailable_storage_prints_the_complete_connected_view(self):
        import json, tempfile
        from pathlib import Path
        from specviz.cli import parser, run

        inv, model = load_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            path.write_text(json.dumps(model))
            output = run(
                parser().parse_args(
                    [
                        "overview",
                        "--project",
                        inv["project"]["root"],
                        "--model",
                        str(path),
                        "--state-dir",
                        inv["project"]["root"],
                    ]
                )
            )
        self.assertLess(output.index("| Node 1 |"), output.index("Component details"))
        self.assertIn("Specification map (10 files)", output)
        self.assertIn("Use show", output)
        self.assertIn("path", output)

    def test_published_large_and_feedback_examples_are_actual_renderer_output(self):
        from large_project_fixture import REPOSITORY

        inv, model = load_fixture()
        example = REPOSITORY / "examples/large-project"
        recorded = __import__("json").loads((example / "model.json").read_text())[
            "snapshot"
        ]
        for detailed in (False, True):
            output = overview_view(inv, model, detailed).render()
            suffix = "-detailed" if detailed else ""
            self.assertEqual(
                output,
                (example / f"overview{suffix}.txt")
                .read_text()
                .replace(recorded, inv["snapshot"]),
            )
        for i, page in enumerate(paginate(overview_view(inv, model)), 1):
            self.assertEqual(
                page.text, (example / f"overview-page-{i}.txt").read_text()
            )
        feedback = Graph(
            [
                Box(
                    "edit",
                    "Revise the request",
                    ["Keep the proposed change until review accepts it."],
                ),
                Box(
                    "review",
                    "Review the request",
                    ["Ask for another revision when a rule is unclear."],
                ),
            ],
            [
                Edge("edit", "review", "request review"),
                Edge("review", "edit", "clarification needed", "condition"),
            ],
        )
        self.assertEqual(
            "\n".join(feedback.draw(80)) + "\n", (example / "feedback.txt").read_text()
        )

    def test_keys_preserve_wide_labels_conditions_markers_and_do_not_expose_files(self):
        graph = self.graph(3, [(0, 1), (1, 2), (2, 0)])
        graph.boxes[0].title = "[changed] " + "清晰的名字" * 12
        graph.boxes[1].body.append("Source: rules.md:L3-7")
        view = View(30, [graph])
        pages = paginate(view, 12)
        self.assertFalse(any(p.documents for p in pages))
        text = " ".join(p.text.replace("|", " ") for p in pages)
        self.assertIn("[changed]", text)
        self.assertIn("condition", text)
        self.assertIn("rules.md:L3-7", text)
        self.assertIn("Inferred", text)
        for edge in graph.edges:
            self.assertIn(edge.caption, " ".join(text.split()))
