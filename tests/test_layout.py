import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/specviz/scripts"))

from specviz.layout import Box, Edge, Graph, TextBlock, View
from specviz.text import display_width


class BoxTests(unittest.TestCase):
    def test_adjacent_branch_arms_join_without_port_fallback(self):
        graph = Graph([Box('start', 'Request a download'), Box('protect', 'Encrypt the file'),
                       Box('plain', 'Continue without protection'), Box('end', 'Download the file')],
                      [Edge('start', 'protect', 'password supplied'), Edge('start', 'plain', 'no password'),
                       Edge('protect', 'end', 'encrypted file'), Edge('plain', 'end', 'unprotected file')])
        text = '\n'.join(graph.draw(80))
        self.assertNotIn('(node ', text)
        for edge in graph.edges:
            self.assertIn(edge.label, text)
        self.assertEqual(text.count('Download the file'), 1)

    def test_complete_explanations_wrap_inside_closed_boxes(self):
        explanation = "If the owner requests protection, encrypt the file before sending it."
        for width in (24, 30, 40, 80):
            with self.subTest(width=width):
                lines = Box("prepare", "Prepare the report", [explanation]).draw(width)
                self.assertTrue(all(display_width(line) == width for line in lines))
                self.assertEqual(lines[0], lines[-1])
                self.assertTrue(all(line.startswith("| ") and line.endswith(" |") for line in lines[1:-1]))
                words = " ".join(line[2:-2].strip() for line in lines[1:-1])
                self.assertIn(explanation, " ".join(words.split()))

    def test_wide_combining_and_long_source_labels_are_not_truncated(self):
        label = "目录/" + "很长的文件名" * 15 + "/e\u0301.md"
        for width in (24, 30, 40, 80):
            lines = Box("wide", label).draw(width)
            self.assertTrue(all(display_width(line) == width for line in lines))
            restored = "".join(line[2:-2].rstrip() for line in lines[1:-1])
            self.assertEqual(restored, label)

    def test_code_indentation_and_control_characters_remain_safe(self):
        lines = Box("code", "Check the request", ["if owner:\n    send_report()\n\x1b[31m"]).draw(40)
        self.assertIn("|     send_report()", "\n".join(lines))
        self.assertNotIn("\x1b", "\n".join(lines))
        self.assertIn("\\x1b", "\n".join(lines))


class GraphTests(unittest.TestCase):
    def graph(self):
        boxes = [Box(name, name.title(), ["Explain what this part does."])
                 for name in ("prepare", "train", "reserve", "predict", "evaluate")]
        edges = [Edge("prepare", "train", "training samples"), Edge("prepare", "reserve", "reserved answers"),
                 Edge("train", "predict", "trained model"), Edge("predict", "evaluate", "predictions"),
                 Edge("reserve", "evaluate", "known answers")]
        return Graph(boxes, edges)

    def test_branch_join_and_long_edge_are_connected_without_duplicate_nodes(self):
        graph = self.graph()
        lines = graph.draw(80)
        text = "\n".join(lines)
        self.assertNotIn("node 1", text, "The ordinary branch and join should route directly")
        self.assertTrue(all(display_width(line) <= 80 for line in lines))
        for box in graph.boxes:
            self.assertEqual(text.count(box.title), 1)
        for edge in graph.edges:
            self.assertIn(edge.caption, text)
        self.assertIn("v", text)
        self.assertEqual(graph.draw(80), lines)

    def test_narrow_graph_has_explicit_endpoints_and_every_relation(self):
        graph = self.graph()
        for width in (24, 30, 40):
            lines = graph.draw(width)
            text = " ".join(line.replace("|", " ") for line in lines)
            self.assertTrue(all(display_width(line) <= width for line in lines))
            self.assertIn("--> Node", text)
            self.assertIn("<-- Node", text)
            for edge in graph.edges:
                self.assertIn(edge.caption, " ".join(text.split()))

    def test_cycle_keeps_return_edge_and_inference_is_marked(self):
        graph = self.graph()
        graph.edges.append(Edge("evaluate", "prepare", "revise inputs", "reference", True))
        text = "\n".join(graph.draw(80))
        self.assertIn("--> Node 1: revise inputs *", text)
        self.assertIn("<-- Node 5: revise inputs *", text)
        self.assertIn("* Inferred relationship", text)
        for box in graph.boxes:
            self.assertEqual(text.count(box.title), 2)

    def test_unrelated_boxes_have_no_execution_arrows(self):
        graph = Graph([Box("one", "Permission one"), Box("two", "Permission two")])
        text = "\n".join(graph.draw(80))
        self.assertNotIn("-->", text)
        self.assertNotIn(" v", text)
        self.assertIn("Permission one", text)
        self.assertIn("Permission two", text)

    def test_relationship_types_keep_their_meaning_and_unknown_endpoints_fail(self):
        for kind in ("containment", "reference", "workflow", "reading", "interaction", "condition"):
            graph = Graph([Box("one", "First part"), Box("two", "Second part")], [Edge("one", "two", kind, kind)])
            self.assertIn(kind, "\n".join(graph.draw(40)))
        graph.edges.append(Edge("unknown", "two", "bad reference"))
        with self.assertRaisesRegex(ValueError, "unknown box"):
            graph.draw(80)


class ViewTests(unittest.TestCase):
    def test_structured_blocks_retain_geometry_and_exposed_references(self):
        view = View(40)
        view.text("Understand the project.")
        graph = Graph([Box("input", "Receive a request"), Box("output", "Return a file")],
                      [Edge("input", "output", "valid request")])
        view.blocks.append(graph)
        view.text("[1] design.md", ("specs/design.md",), "Files under specs/:")
        view.text("[2] rules.md", ("specs/rules.md",), "Files under specs/:")
        output = view.render()
        self.assertIn("\n".join(graph.draw(40)), output)
        self.assertEqual(output.count("Files under specs/:"), 1)
        self.assertEqual(view.documents, ("specs/design.md", "specs/rules.md"))
        self.assertTrue(all(display_width(line) <= 40 for line in output.splitlines()))

    def test_separate_panels_preserve_graph_identity_and_endpoints(self):
        graph = GraphTests().graph()
        panels = graph.panels()
        self.assertEqual([panel.identity for panel in panels], [box.identity for box in graph.boxes])
        for index, box in enumerate(graph.boxes):
            panel = panels[index]
            self.assertEqual(panel.title, box.title)
            for edge in graph.edges:
                if edge.origin == box.identity:
                    self.assertTrue(any(note.startswith("--> Node") and edge.caption in note for note in panel.body))
                if edge.target == box.identity:
                    self.assertTrue(any(note.startswith("<-- Node") and edge.caption in note for note in panel.body))


if __name__ == "__main__":
    unittest.main()
