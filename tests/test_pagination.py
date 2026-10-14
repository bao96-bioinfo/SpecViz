import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/specviz/scripts'))
from specviz.layout import Box, Edge, Graph, View
from specviz.pagination import paginate
from specviz.text import display_width
from diagram_fixture import load_fixture
from specviz.views import overview_view, show_view


class PaginationTests(unittest.TestCase):
    def check_pages(self, pages, budget, width):
        for page in pages:
            self.assertLessEqual(len(page.text.splitlines()), budget)
            self.assertTrue(all(display_width(line) <= width for line in page.text.splitlines()))
            opened = False
            for line in page.text.splitlines():
                if line.startswith('+') and line.endswith('+'):
                    opened = not opened
                elif line.startswith('|'):
                    self.assertTrue(opened, line)
                    self.assertTrue(line.endswith('|'), line)
            self.assertFalse(opened, page.text)

    def test_minimum_budget_closes_oversized_nodes_and_preserves_all_content(self):
        view = View(30)
        view.blocks.append(Graph([Box('one', 'First compartment', [f'Unique sentence {i:02d}.' for i in range(30)]),
                                  Box('two', 'Second compartment', ['End of supported process.'])],
                                 [Edge('one', 'two', 'only when accepted')]))
        pages = paginate(view, 12)
        self.check_pages(pages, 12, 30)
        combined = '\n'.join(page.text for page in pages)
        for i in range(30):
            self.assertEqual(combined.count(f'Unique sentence {i:02d}.'), 1)
        self.assertIn('--> Node 2:', combined)
        self.assertIn('<-- Node 1:', combined)
        self.assertEqual(' '.join(combined.replace('|', ' ').split()).count('only when accepted'), 3)
        self.assertIn('(continued)', combined)
        self.assertIn('Next: Diagram', combined)

    def test_source_keys_are_complete_and_carry_only_their_own_identities(self):
        view = View(30)
        prefix = 'Files under ' + 'long-folder/' * 30
        for i in range(5):
            view.text(f'[{i+1}] file-{i}.md', (f'doc-{i}',), prefix)
        pages = paginate(view, 12)
        self.check_pages(pages, 12, 30)
        for i in range(5):
            contributors = [page for page in pages if f'doc-{i}' in page.documents]
            self.assertTrue(contributors)
            text = ' '.join(page.text.replace('\n', ' ') for page in contributors)
            self.assertIn(f'[{i+1}] file-{i}.md', text)
            self.assertGreater(len(contributors), 1)

    def test_fixture_detailed_view_and_narrow_overview_have_no_lost_content(self):
        inventory, model = load_fixture()
        for width in (30, 80):
            for view in (overview_view(inventory, model, width=width),
                         show_view(inventory, model=model, detailed=True, width=width)):
                pages = paginate(view, 12)
                self.check_pages(pages, 12, width)
                self.assertEqual(set(view.documents), {doc for page in pages for doc in page.documents})
                text = ''.join(page.text for page in pages)
                self.assertIn('End of this view.', text)
                for block in view.blocks:
                    if isinstance(block, Graph):
                        for edge in block.edges:
                            self.assertIn(edge.label, ' '.join(text.replace('|', ' ').split()))


if __name__ == '__main__':
    unittest.main()
