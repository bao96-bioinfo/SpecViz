import copy
import unittest

from diagram_fixture import load_fixture
from specviz.layout import Graph
from specviz.core import validate_model
from specviz.render import render_overview, render_show, display_width
from specviz.views import overview_view
from test_render import sample_inventory


def words(text):
    return " ".join(text.replace("|", " ").split())


class DiagramViewTests(unittest.TestCase):
    def test_legacy_model_uses_known_document_links_without_inventing_a_process(self):
        inventory, model = load_fixture()
        del model["project_view"]
        before = copy.deepcopy(inventory)
        validate_model(model, inventory)
        output = render_overview(inventory, model)
        self.assertIn("Project relationships unresolved", output)
        self.assertIn("+---", output)
        self.assertIn("Document dependency inferred from the framework layout", words(output))
        self.assertNotIn("training samples", output)
        for number, document in enumerate(inventory["documents"], 1):
            self.assertIn(f"[{number}]", output)
        self.assertEqual(inventory, before)

    def test_uninterpreted_sources_remain_explicit_and_complete_in_detail(self):
        inventory = sample_inventory()
        before = copy.deepcopy(inventory)
        output = render_show(inventory, ["requirements.md"], detailed=True)
        self.assertIn("Interpretation unavailable", output)
        self.assertIn("[unresolved]", output)
        for block in inventory["documents"][0]["blocks"]:
            if block["kind"] != "heading":
                self.assertIn(words(block["text"]), words(output))
        self.assertEqual(inventory, before)

    def test_duplicate_basenames_and_shared_prefixes_have_exact_keys(self):
        inventory, model = load_fixture()
        view = overview_view(inventory, model)
        output = view.render()
        for index, document in enumerate(inventory["documents"], 1):
            short = document["path"].removeprefix("openspec/changes/reproducible-model-training/")
            self.assertIn(f"[{index}] {short}", output)
        self.assertIn("[3] specs/data-preparation/spec.md", output)
        self.assertIn("[4] specs/evaluation/spec.md", output)
        keys = [block for block in view.blocks if block.documents]
        self.assertEqual(len(keys), 8)

    def test_large_group_accounts_for_every_file_without_repeating_purposes(self):
        inventory = sample_inventory()
        template = inventory["documents"][0]
        inventory["documents"] = [dict(template, id=f"rules/{index}/spec.md", path=f"rules/{index}/spec.md")
                                  for index in range(120)]
        inventory["scope"] = [doc["id"] for doc in inventory["documents"]]
        inventory["relationships"] = []
        view = overview_view(inventory)
        output = view.render()
        self.assertIn("120 files", output)
        self.assertIn("layout group", output)
        self.assertEqual(set(view.documents), set(inventory["scope"]))
        for index in range(120):
            self.assertIn(f"[{index + 1}] {index}/spec.md", output)
        self.assertEqual(output.count("Files (120 files) under rules/:"), 1)

    def test_local_context_history_and_whole_project_numbering_stay_distinct(self):
        inventory = sample_inventory()
        inventory["scope"] = ["design.md"]
        inventory["context"] = ["requirements.md"]
        output = render_overview(inventory)
        self.assertIn("[2] design.md", output)
        self.assertIn("[1] requirements.md [context]", words(output))
        self.assertIn("<-- file [1]", output)
        self.assertIn("Related context outside selected scope (1 file)", output)
        self.assertNotIn("tasks.md", output)
        inventory = sample_inventory()
        inventory["groups"][0]["lifecycle"] = "archived"
        inventory["current_work"] = "new-export"
        output = render_overview(inventory)
        self.assertIn("[history]", output)
        self.assertIn("Current work: new-export", output)
        self.assertIn("Specification map (3 files)", output)
        self.assertIn("[3] tasks.md", output)

    def test_eight_file_overview_is_connected_and_keeps_references_secondary(self):
        inventory, model = load_fixture()
        before = copy.deepcopy(inventory)
        view = overview_view(inventory, model)
        output = view.render()
        self.assertEqual(render_overview(inventory, model), output)
        self.assertIn("Specification map (8 files)", output)
        self.assertNotIn("Relationships (", output)
        self.assertNotIn("Source snapshot", output)
        self.assertNotIn(inventory["snapshot"], output)
        self.assertNotIn("node 1", output, "This ordinary branch and join should route directly")
        self.assertEqual(output.count("openspec/changes/reproducible-model-training/"), 1)
        self.assertTrue(all(display_width(line) <= 80 for line in output.splitlines()))
        self.assertEqual(set(view.documents), set(inventory["scope"]))
        # Read each column independently; adjacent boxes must not interleave
        # the sentences during a plain row-by-row text comparison.
        columns = [words("\n".join(line[start:start + 38] for line in output.splitlines()))
                   for start in (0, 21, 42)]
        for node in model["project_view"]["nodes"]:
            self.assertIn(node["label"], words(output))
            self.assertTrue(any(node["summary"] in column for column in columns), node["summary"])
        self.assertIn("threshold is still undecided", words(output))
        self.assertEqual(inventory, before)

    def test_detailed_overview_preserves_the_project_graph_and_expands_coverage(self):
        inventory, model = load_fixture()
        concise = overview_view(inventory, model)
        detailed = overview_view(inventory, model, detailed=True)
        concise_graph = next(block for block in concise.blocks if isinstance(block, Graph))
        detailed_graph = next(block for block in detailed.blocks if isinstance(block, Graph))
        self.assertEqual(concise_graph, detailed_graph)
        output = detailed.render()
        self.assertIn(inventory["snapshot"], output)
        self.assertIn("Source: lines", output)
        for doc in model["documents"]:
            for item in doc["items"]:
                for note in item["notes"]:
                    self.assertIn(words(note), words(output))
