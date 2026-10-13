"""Meaning-preserving text layout checks, including sources and incomplete evidence."""

from __future__ import annotations

import unittest
from pathlib import Path

from specviz.core import parse_blocks, validate_model
from specviz.render import display_width, render_changes, render_overview, render_show, split_pages, wrap_text


GOLDEN = Path(__file__).parent / "golden"


def sample_inventory():
    texts = {
        "requirements.md": "# Export rules\n\nExport reports without sharing account secrets.\n\n## Export time\n\nExports MUST finish within 30 seconds, except files larger than 2 gigabytes.\n\n## Access\n\nGuests MUST NOT export private reports. Administrators MAY allow public exports.\n\n## Open question\n\nWhether to allow encrypted archives remains undecided.\n",
        "design.md": "# Export design\n\nProtect exported reports with a password.\n\n## Request\n\nThe user asks the export service for a report.\n\n## Processing\n\nThe export service asks storage for report data.\n\n## Delivery\n\nThe export service returns a password-protected file to the user.\n",
        "tasks.md": "# Implementation steps\n\nAdd password protection to report export.\n\n- [ ] Preserve existing exports.\n- [ ] Add encryption.\n"
    }
    documents = []
    for path, text in texts.items():
        documents.append({"id": path, "path": path, "hash": path + "-version-1", "text": text,
                          "blocks": parse_blocks(text, path), "purpose": text.splitlines()[2],
                          "title": text.splitlines()[0][2:], "group": "data-export", "framework": "Example",
                          "role": {"requirements.md": "Requirements", "design.md": "Design", "tasks.md": "Tasks"}[path],
                          "lifecycle": "active"})
    return {"schema_version": 1, "snapshot": "example-source-version-1", "project": {
        "root": "/example", "id": "example", "name": "Reporting service", "purpose": "Export and share reports safely."},
        "documents": documents, "groups": [{"id": "data-export", "label": "Data export", "purpose": "Produce downloadable reports.", "lifecycle": "active"}],
        "relationships": [{"from": "requirements.md", "to": "design.md", "type": "workflow", "label": "defines the design's rules", "inferred": False},
                          {"from": "design.md", "to": "tasks.md", "type": "workflow", "label": "guides implementation", "inferred": True}],
        "scope": list(texts), "context": [], "warnings": []}


def sample_model(inventory, layout="tree"):
    doc = inventory["documents"][1]
    bodies = [block for block in doc["blocks"] if block["kind"] != "heading"]
    labels = ["Protect exported reports", "User requests export", "Export service reads report", "User receives protected file"]
    items = [{"id": f"step-{index}", "label": label, "kind": "goal" if index == 0 else "behavior",
              "sources": [body["id"]], "notes": [body["text"]]} for index, (body, label) in enumerate(zip(bodies, labels))]
    return {"schema_version": 1, "snapshot": inventory["snapshot"], "documents": [{
        "id": doc["id"], "purpose": "How password-protected export works.", "layout": layout,
        "items": items, "relationships": [
            {"from": "step-1", "to": "step-2", "type": "workflow" if layout != "interaction" else "interaction", "label": "request starts data retrieval", "inferred": False},
            {"from": "step-2", "to": "step-3", "type": "workflow", "label": "result is encrypted and returned", "inferred": True}]}]}


def sample_comparison():
    return {"basis": "Workflow completion report from the previous implementation round.", "warnings": [], "rows": [
        {"document": "requirements.md", "requirement_id": "Export time", "requested": "Exports finish within 30 seconds except files larger than 2 gigabytes.",
         "implemented": "Exports finish within 30 seconds except files larger than 2 gigabytes.", "difference": "unchanged", "status": "reported implemented",
         "evidence": {"origin": "Previous round", "coverage": "complete"}, "verification": {"check": "export timing", "result": "passed"}},
        {"document": "design.md", "requirement_id": "Password protection", "requested": "Protect exported reports with a password.",
         "implemented": "Return an unencrypted report file.", "difference": "behavioral", "status": "reported implemented", "reason": "Requested protection is not covered by the earlier report.",
         "evidence": {"origin": "Previous round", "coverage": "complete"}, "verification": None},
        {"document": "tasks.md", "requirement_id": "Implementation steps", "requested": "Add password protection to report export.",
         "implemented": "Add password protection to report export.", "difference": "unchanged", "status": "reported implemented", "verification": None}]}


class RenderTests(unittest.TestCase):
    def test_four_layout_golden_outputs(self):
        inventory = sample_inventory()
        for layout in ("tree", "flow", "interaction", "rules"):
            with self.subTest(layout=layout):
                rendered = render_show(inventory, ["design.md"], sample_model(inventory, layout))
                self.assertEqual(rendered, (GOLDEN / f"{layout}.txt").read_text(encoding="utf-8"))
                self.assertIn("request starts data retrieval", " ".join(rendered.split()))
                self.assertIn("(inferred)", rendered)
                self.assertTrue(all(ord(char) < 128 for char in rendered))

    def test_details_preserve_nodes_and_relationships(self):
        inventory = sample_inventory()
        for layout in ("tree", "flow", "interaction", "rules"):
            model = sample_model(inventory, layout)
            concise = render_show(inventory, ["design.md"], model)
            detailed = render_show(inventory, ["design.md"], model, detailed=True)
            skeleton = lambda value: [line for line in value.splitlines() if line.startswith(("+--", "|   +--", "| ("))]
            self.assertEqual(skeleton(concise), skeleton(detailed))
            for item in model["documents"][0]["items"]:
                self.assertIn(item["label"], concise)
                self.assertIn(item["label"], detailed)
            self.assertIn("password-protected", detailed)

    def test_exact_fallback_preserves_conditions_and_unknown_question(self):
        rendered = render_show(sample_inventory(), ["requirements.md"], detailed=True)
        flattened = " ".join(rendered.replace("|", " ").split())
        self.assertIn("Interpretation unavailable", rendered)
        self.assertIn("[unresolved]", rendered)
        for meaning in ("30 seconds", "2 gigabytes", "except files larger", "Guests MUST NOT", "Administrators MAY", "remains undecided"):
            self.assertIn(meaning, flattened)
        self.assertIn("File [1]: requirements.md", rendered)
        self.assertIn("Source: lines 5-7", rendered)
        self.assertIn("Source: lines 9-11", rendered)
        self.assertIn("Source: lines 13-15", rendered)

    def test_unresolved_model_content_is_explicit_and_exact(self):
        inventory = sample_inventory()
        model = sample_model(inventory)
        body = inventory["documents"][1]["blocks"][-1]
        model["documents"][0]["items"] = model["documents"][0]["items"][:-1]
        model["documents"][0]["relationships"] = []
        model["documents"][0]["unresolved"] = [body["id"]]
        rendered = render_show(inventory, ["design.md"], model, detailed=True)
        self.assertIn("[unresolved]", rendered)
        self.assertIn("password-protected", rendered)
        self.assertIn("Source: lines " + str(body["start_line"]), rendered)

    def test_explicit_containment_is_a_tree_and_cycles_remain_visible(self):
        inventory = sample_inventory()
        model = sample_model(inventory)
        relationships = model["documents"][0]["relationships"]
        relationships[:] = [{"from": "step-0", "to": "step-1", "type": "containment", "label": "contains this behavior"}]
        rendered = render_show(inventory, ["design.md"], model)
        self.assertIn("|   +-- (2) User requests export", rendered)
        relationships.append({"from": "step-1", "to": "step-0", "type": "containment", "label": "cycle in source"})
        cyclic = render_show(inventory, ["design.md"], model)
        self.assertIn("cycle in source", cyclic)
        for index in range(1, 5):
            self.assertEqual(cyclic.count(f"({index})"), 1)

    def test_wide_long_and_combining_labels_respect_body_width(self):
        inventory = sample_inventory()
        inventory["documents"][0]["path"] = "目录/" + "很长的文件名" * 30 + "/e\u0301.md"
        inventory["documents"][0]["purpose"] = "文件说明 " * 40
        rendered = render_overview(inventory, detailed=True)
        self.assertTrue(all(display_width(line) <= 80 for line in rendered.splitlines()))
        self.assertIn("e\u0301.md", rendered)
        self.assertEqual(display_width("e\u0301中文"), 5)
        self.assertEqual("".join(wrap_text(inventory["documents"][0]["path"], 72)), inventory["documents"][0]["path"])

    def test_many_files_counted_and_not_omitted(self):
        inventory = sample_inventory()
        template = inventory["documents"][0]
        inventory["documents"] = [dict(template, id=f"spec-{index}.md", path=f"spec-{index}.md") for index in range(120)]
        inventory["scope"] = [doc["id"] for doc in inventory["documents"]]
        inventory["relationships"] = []
        rendered = render_overview(inventory)
        self.assertIn("(120 files)", rendered)
        for index in range(120):
            self.assertIn(f"[{index + 1}] spec-{index}.md", rendered)

    def test_scope_preserves_global_selection_numbers_and_labels_context(self):
        inventory = sample_inventory()
        inventory["scope"] = ["design.md"]
        inventory["context"] = ["requirements.md"]
        rendered = render_overview(inventory)
        self.assertIn("[2] design.md", rendered)
        self.assertIn("Related context outside selected scope (1 file)", rendered)
        self.assertIn("requirements.md - Export", rendered)
        self.assertNotIn("[1] requirements.md", rendered)

    def test_current_work_annotation_keeps_the_entire_project(self):
        inventory = sample_inventory()
        inventory["current_work"] = "openspec/changes/password-export"
        rendered = render_overview(inventory)
        self.assertIn("Current work: openspec/changes/password-export", rendered)
        self.assertIn("Specification map (3 files)", rendered)
        self.assertIn("[3] tasks.md", rendered)

    def test_no_background_purpose_is_explicit(self):
        inventory = sample_inventory()
        inventory["project"]["purpose"] = ""
        inventory["documents"][0]["purpose"] = ""
        rendered = render_overview(inventory)
        self.assertIn("Purpose: Unspecified", rendered)
        self.assertIn("Purpose unspecified", rendered)

    def test_comparison_highlights_ancestors_and_preserves_other_files(self):
        inventory = sample_inventory()
        comparison = sample_comparison()
        concise = render_changes(inventory, comparison)
        detailed = render_changes(inventory, comparison, detailed=True)
        self.assertEqual(concise, (GOLDEN / "changes.txt").read_text(encoding="utf-8"))
        self.assertIn("[contains changes] Data export", concise)
        self.assertIn("[changed] [2] design.md", concise)
        self.assertIn("[changed] Password protection", concise)
        self.assertIn("[1] requirements.md", concise)
        self.assertIn("[3] tasks.md", concise)
        self.assertIn("Verification: Unavailable", concise)
        self.assertIn("Earlier reported behavior: Return an unencrypted report file.", detailed)
        self.assertIn("Evidence status: Earlier behavior reported implemented", concise)
        self.assertIn("changes --detailed", concise)
        self.assertIn("changes --check-code", concise)
        self.assertIn("Completion evidence:", detailed)

    def test_no_evidence_remains_unknown_not_unimplemented(self):
        rendered = render_changes(sample_inventory(), {"rows": [], "warnings": []})
        self.assertIn("[contains attention] Data export", rendered)
        self.assertIn("Implementation unknown", rendered)
        self.assertNotIn("[changed] [", rendered)
        self.assertNotIn("unimplemented", rendered)

    def test_comparison_uses_model_labels_for_the_correct_document(self):
        inventory = sample_inventory()
        comparison = sample_comparison()
        comparison["rows"][1]["requirement_id"] = "step-0"
        rendered = render_changes(inventory, comparison, sample_model(inventory), detailed=True)
        self.assertIn("[changed] Protect exported reports", rendered)
        self.assertIn("Source identifier: step-0", rendered)

    def test_conflicting_inspection_retains_report_and_findings(self):
        comparison = sample_comparison()
        comparison["rows"][1]["inspection"] = {"status": "contradicted", "source": "export.py:8", "observation": "Returns plaintext."}
        rendered = render_changes(sample_inventory(), comparison, detailed=True)
        self.assertIn("Previous round", rendered)
        self.assertIn("contradicted", rendered)
        self.assertIn("Returns plaintext.", rendered)
        self.assertIn("does not complete a workflow round", rendered)

    def test_partial_evidence_details_are_visible_without_retained_snapshots(self):
        comparison = sample_comparison()
        comparison["rows"][1]["evidence"] = {
            "event_id": "report-1", "round_id": "round-1", "framework": "OpenSpec",
            "origin": {"kind": "handoff", "source": "Implementation progress report"},
            "coverage": {"status": "partial", "version_bound": True,
                         "details": {"supported": "Password input", "outstanding": "Encryption"}},
            "specification": {"path": "design.md", "hash": "version-1"},
            "implementation": {"files": {"export.py": "hash"}, "complete_manifest": False},
            "snapshots": "RETAINED SNAPSHOT MUST NOT BE REPEATED"}
        rendered = render_changes(sample_inventory(), comparison, detailed=True)
        self.assertIn("Password input", rendered)
        self.assertIn("Encryption", rendered)
        self.assertIn("1 bound source files", rendered)
        self.assertNotIn("RETAINED SNAPSHOT MUST NOT BE REPEATED", rendered)

    def test_current_code_support_keeps_earlier_workflow_behavior_distinct(self):
        comparison = sample_comparison()
        row = comparison["rows"][1]
        row.update(status="code supported", difference="unchanged", report_status="reported implemented",
                   report_difference="behavioral", difference_basis="current code inspection")
        row["inspection"] = {"finding": {"status": "supported", "reason": "Current export encrypts the file.",
                                       "locations": [{"path": "export.py", "line": 15}]}, "record": {"complete": True}}
        rendered = render_changes(sample_inventory(), comparison, detailed=True)
        self.assertIn("Current code supports requested behavior", rendered)
        self.assertIn("Earlier reported behavior: Return an unencrypted report file.", rendered)
        self.assertIn("Earlier report comparison: behavioral", rendered)
        self.assertIn("Earlier behavior verification: Unavailable", rendered)
        self.assertNotIn("[changed] [2] design.md", rendered)
        self.assertNotIn("[changed] Password protection", rendered)

    def test_code_support_without_reports_does_not_imply_an_unchanged_baseline(self):
        comparison = sample_comparison()
        row = comparison["rows"][1]
        row.update(status="code supported", difference="unchanged", report_status="unknown",
                   report_difference="unresolved", difference_basis="current code inspection", evidence=None, implemented=None)
        rendered = render_changes(sample_inventory(), comparison)
        self.assertIn("Difference vs inspected code: none identified", rendered)
        self.assertIn("Workflow report reference: unavailable", rendered)
        self.assertNotIn("Earlier report comparison: unresolved", rendered)

    def test_concise_changes_summarize_source_but_keep_conflicts_and_limits(self):
        comparison = sample_comparison()
        row = comparison["rows"][1]
        requested = "Guests MUST NOT export private reports. Owners MAY export up to 100 rows within 30 seconds, except explicitly approved audit reports."
        implemented = "All users may export reports without an ownership check."
        row.update(requested=requested, implemented=implemented, status="contradicted",
                   reason="Code allows guests instead of enforcing report ownership.",
                   sources=["design.md:L5-12"], evidence={"event_id": "earlier-owner-report", "specification": {"hash": "old-source-version"}},
                   verification={"executed": True, "checks": [{"command": "python -m unittest test_ownership", "result": "passed"}]})
        row["inspection"] = {"record": {"complete": False, "inspection_id": "owner-inspection"}, "finding": {
            "status": "contradicted", "reason": row["reason"], "locations": [{"path": "private_export.py", "line": 22}],
            "uninspected": ["Audit report exceptions"], "tests": {"executed": False, "definitions": ["test_export.py:8"]}}}
        concise = render_changes(sample_inventory(), comparison)
        detailed = render_changes(sample_inventory(), comparison, detailed=True)
        plain = lambda text: " ".join(text.replace("|", " ").split())
        for output in (concise, detailed):
            self.assertIn("Current code contradicts requested behavior", plain(output))
            self.assertIn("Audit report exceptions", plain(output))
            self.assertIn("tests were not executed", plain(output))
            self.assertIn("Earlier behavior verification:", output)
        self.assertNotIn("Requested:", concise)
        self.assertNotIn("Guests MUST NOT export", concise)
        self.assertNotIn(implemented, concise)
        for metadata in ("old-source-version", "design.md:L5-12", "private_export.py:22", "owner-inspection", "test_ownership"):
            self.assertNotIn(metadata, concise)
            self.assertIn(metadata, plain(detailed))
        self.assertIn(requested, plain(detailed))
        self.assertIn(implemented, plain(detailed))
        self.assertIn("Full source wording is available with --detailed", plain(concise))

    def test_snapshot_and_workflow_labels_are_plain_and_concrete(self):
        inventory = sample_inventory()
        inventory["relationships"][0]["label"] = "Requirements first workflow"
        rendered = render_overview(inventory)
        self.assertIn("Source snapshot:", rendered)
        self.assertIn("requirements guide the design", rendered)
        self.assertNotIn("Requirements first workflow", rendered)

    def test_missing_historical_documents_remain_in_the_change_hierarchy(self):
        inventory = sample_inventory()
        comparison = sample_comparison()
        for number in range(2):
            comparison["rows"].append({
                "document": "former/export-rules.md", "requirement_id": f"former-rule-{number + 1}",
                "requested": "Source unavailable", "implemented": ("Owners may download private reports." if number == 0 else "Passwords must never appear in logs."),
                "status": "unknown", "difference": "source-unavailable", "evidence": {"origin": "Earlier report", "coverage": "complete"},
                "reason": "A missing or moved document does not establish a behavior-removal request.",
                "verification": None, "inspection": None})
        for detailed in (False, True):
            rendered = render_changes(inventory, comparison, detailed=detailed)
            flattened = " ".join(rendered.replace("|", " ").split())
            self.assertIn("Historical source correspondence unresolved", flattened)
            self.assertIn("[source unavailable] former/export-rules.md", rendered)
            self.assertIn("Historical file: former/export-rules.md", rendered)
            self.assertIn("2 requirements with unresolved correspondence", flattened)
            if detailed:
                self.assertIn("Earlier reported behavior: Owners may download private reports.", flattened)
                self.assertIn("Passwords must never appear in logs.", flattened)
            else:
                self.assertNotIn("Owners may download private reports.", flattened)
                self.assertNotIn("Passwords must never appear in logs.", flattened)
            self.assertIn("Implementation unknown", rendered)
            self.assertIn("does not establish a behavior-removal request", flattened)
            self.assertNotIn("[changed] former", rendered)
            self.assertNotIn("[removed]", rendered)
            self.assertTrue(all(display_width(line) <= 80 for line in rendered.splitlines()))

    def test_temporally_uncertain_report_candidates_are_traceable_in_detail(self):
        comparison = sample_comparison()
        row = comparison["rows"][1]
        row.update(status="unknown", difference="unresolved", temporal_order_uncertain=True,
                   candidate_report_difference="unchanged", report_alternatives=[{
                       "event_id": "earlier-report-2", "round_id": "round-2",
                       "origin": {"source": "Another completion report", "kind": "handoff"},
                       "specification": {"path": "design.md", "hash": "alternative-version"},
                       "implemented": "Protect exported files with a password."}])
        concise = render_changes(sample_inventory(), comparison)
        detailed = render_changes(sample_inventory(), comparison, detailed=True)
        self.assertIn("no candidate is confirmed as the latest", " ".join(concise.replace("|", " ").split()))
        self.assertIn("Candidate report comparison: unchanged", detailed)
        self.assertIn("earlier-report-2", detailed)
        self.assertIn("alternative-version", detailed)
        self.assertIn("Protect exported files with a password.", detailed)
        self.assertIn("Return an unencrypted report file.", detailed)

    def test_incomplete_inspection_and_unexecuted_tests_are_explicit(self):
        comparison = sample_comparison()
        comparison["rows"][1]["inspection"] = {
            "record": {"inspection_id": "inspection-1", "complete": False},
            "finding": {"status": "partial", "reason": "Owner check found; encryption not inspected.",
                        "locations": [{"path": "export.py", "line": 12}], "uninspected": ["Encryption"],
                        "tests": {"executed": False, "locations": ["test_export.py:8"]}}}
        rendered = render_changes(sample_inventory(), comparison, detailed=True)
        self.assertIn("Uninspected scope", rendered)
        self.assertIn("Incomplete; continue inspection", rendered)
        self.assertIn("export.py:12", rendered)
        self.assertIn("tests were not executed", rendered)
        self.assertNotIn('"result": "passed"', rendered)

    def test_continuation_is_snapshot_bound_and_no_lines_disappear(self):
        original = "\n".join(f"Line {index}: selected specification content" for index in range(47)) + "\n"
        pages = split_pages(original, "source-version-1", max_lines=8)
        self.assertEqual(len(pages), 6)
        for index, page in enumerate(pages):
            self.assertIn(f"Part {index + 1} of 6", page)
            self.assertIn("source-version-1", page)
            if index < len(pages) - 1:
                self.assertIn("content lines remain", page)
                self.assertNotIn("Complete: all", page)
        combined = "\n".join(pages)
        for line in original.splitlines():
            self.assertEqual(combined.count(line + "\n"), 1)
        self.assertIn("Complete: all selected content", pages[-1])

    def test_empty_and_unreadable_scope_is_actionable(self):
        inventory = sample_inventory()
        inventory["documents"] = []
        inventory["scope"] = []
        inventory["warnings"] = ["design.md cannot be read; coverage incomplete."]
        rendered = render_overview(inventory)
        self.assertIn("Select a Markdown file explicitly", rendered)
        self.assertIn("coverage incomplete", rendered)

    def test_control_characters_do_not_escape_into_terminal(self):
        inventory = sample_inventory()
        inventory["project"]["name"] = "Report\x1b[31m"
        rendered = render_overview(inventory)
        self.assertNotIn("\x1b", rendered)
        self.assertIn("\\x1b", rendered)

    def test_exact_source_notes_retain_common_code_and_list_indentation(self):
        note = "if owner:\n    allow_download()\n- Rules\n  - Keep passwords private"
        self.assertEqual(wrap_text(note, 76), note.splitlines())

    def test_task_nodes_reference_their_own_source_and_do_not_repeat_the_list(self):
        inventory = sample_inventory()
        inventory["scope"] = ["tasks.md"]
        document = inventory["documents"][2]
        lists = [block for block in document["blocks"] if block["kind"] == "list"]
        self.assertEqual(len(lists), 2)
        introduction = [block for block in document["blocks"] if block["kind"] != "list"]
        items = [{"id": "export-work", "label": "Work for protected exports", "kind": "goal",
                  "sources": [block["id"] for block in introduction], "notes": [document["purpose"]]}]
        for index, (block, label) in enumerate(zip(lists, ("Preserve existing exports", "Add encryption")), 1):
            items.append({"id": f"task-{index}", "label": label, "kind": "task",
                          "sources": [block["id"]], "notes": [block["text"]]})
        model = {"schema_version": 1, "snapshot": inventory["snapshot"], "documents": [{
            "id": "tasks.md", "purpose": "Work for protected exports", "layout": "tree", "items": items}]}
        validate_model(model, inventory)
        rendered = render_show(inventory, ["tasks.md"], model, detailed=True)
        self.assertEqual(rendered.count("[ ] Preserve existing exports."), 1)
        self.assertEqual(rendered.count("[ ] Add encryption."), 1)
        self.assertIn("Source: lines 5", rendered)
        self.assertIn("Source: lines 6", rendered)

    def test_continuation_names_remaining_files_in_an_overview(self):
        inventory = sample_inventory()
        pages = split_pages(render_overview(inventory), inventory["snapshot"], max_lines=8)
        self.assertTrue(any("Remaining files:" in page and "tasks.md" in page for page in pages[:-1]))


if __name__ == "__main__":
    unittest.main()
