"""Structured, source-backed views shared by string rendering and pagination."""

from __future__ import annotations

from .layout import Box, Edge, Graph, View
from .render import (_documents, _file_count, _groups, _items, _item_notes,
                     _model_documents, _numbers, _purpose, _snapshot, _source_refs,
                     _active_change, _comparison_row, _Writer)
from .text import clean


def start_view(inventory: dict, model: dict | None, width: int) -> View:
    view = View(width)
    project = inventory.get("project", {})
    name = str(project.get("name") or "")
    purpose = str((model or {}).get("project_purpose") or project.get("purpose") or "Purpose unspecified")
    prefix = name + " - " if name.casefold() not in {"", "project", "unnamed project"} else ""
    view.text(prefix + purpose)
    if inventory.get("current_work"):
        view.text("Current work: " + clean(inventory["current_work"]))
    return view


def finish_view(view: View, inventory: dict, detailed: bool, hint: str = "") -> View:
    for warning in inventory.get("warnings", []):
        view.text("Unresolved: " + clean(warning.get("message", warning) if isinstance(warning, dict) else warning))
    if detailed:
        view.text("Source snapshot:\n" + _snapshot(inventory))
    if hint:
        view.text(hint)
    return view


def path_prefix(documents: list[dict]) -> str:
    shared = []
    for parts in zip(*(str(doc["path"]).split("/")[:-1] for doc in documents)):
        if len(set(parts)) != 1:
            break
        shared.append(parts[0])
    return "/".join(shared) + "/" if shared else ""


def file_key(view: View, inventory: dict, documents: list[dict], context: bool = False) -> None:
    numbers = _numbers(inventory)
    groups = _groups(inventory, documents)
    for group, members in groups:
        prefix = path_prefix(members)
        state = "; history" if group.get("lifecycle") in {"archive", "archived", "history", "historical"} else ""
        heading = ("Related context outside selected scope" if context else "Files") + f" ({_file_count(len(members))}{state})"
        if len(groups) > 1:
            heading += " - " + str(group.get("label") or "Unnamed group")
        heading += (" under " + prefix if prefix else "") + ":"
        for document in members:
            suffix = " [context] - " + _purpose(document) if context else ""
            view.text(f"[{numbers[document['id']]}] {document['path'][len(prefix):]}{suffix}", (document["id"],), heading)


def edges(relations: list[dict], identities: set[str]) -> list[Edge]:
    meanings = {"Requirements first workflow": "requirements guide the design",
                "Design first workflow": "design guides the requirements"}
    return [Edge(str(r["from"]), str(r["to"]), meanings.get(str(r.get("label")), str(r.get("label") or r.get("type") or "Relationship unspecified")),
                 str(r.get("type") or "reference"), bool(r.get("inferred")))
            for r in relations if r.get("from") in identities and r.get("to") in identities]


def document_map(view: View, inventory: dict, documents: list[dict], model: dict | None,
                 markers: dict[str, str] | None = None, group_markers: dict[str, str] | None = None) -> None:
    numbers, interpreted = _numbers(inventory), _model_documents(model)
    markers, group_markers = markers or {}, group_markers or {}
    grouped = _groups(inventory, documents)
    if len(grouped) > 1:
        owners = {d["id"]: str(g["id"]) for g, members in grouped for d in members}
        group_boxes = [Box(str(g["id"]), group_markers.get(str(g["id"]), "") +
                           str(g.get("label") or g["id"]) + f" ({_file_count(len(members))})")
                       for g, members in grouped]
        group_edges = [Edge(owners[e.origin], owners[e.target],
                            f"file [{numbers[e.origin]}] to [{numbers[e.target]}]: {e.label}", e.kind, e.inferred)
                       for e in edges(inventory.get("relationships", []), set(owners))
                       if owners[e.origin] != owners[e.target]]
        view.blocks.append(Graph(group_boxes, group_edges, "Document groups"))
    for group, members in grouped:
        identity = str(group["id"])
        title = group_markers.get(identity, "") + str(group.get("label") or identity) + f" ({_file_count(len(members))})"
        if group.get("lifecycle") in {"archive", "archived", "history", "historical"}:
            title += " [history]"
        prefix = path_prefix(members)
        boxes = [Box(doc["id"], markers.get(doc["id"], "") + f"[{numbers[doc['id']]}] " + doc["path"][len(prefix):],
                     [_purpose(doc, interpreted.get(doc["id"]))]) for doc in members]
        ids = {doc["id"] for doc in members}
        relations = edges(inventory.get("relationships", []), ids)
        all_edges = edges(inventory.get("relationships", []),
                          {doc["id"] for doc in documents} | set(inventory.get("context", [])))
        for box in boxes:
            for edge in all_edges:
                if edge.origin == box.identity and edge.target not in ids:
                    box.body.append(f"--> file [{numbers[edge.target]}]: {edge.caption}")
                if edge.target == box.identity and edge.origin not in ids:
                    box.body.append(f"<-- file [{numbers[edge.origin]}]: {edge.caption}")
        legend = "* Document dependency inferred from the framework layout."
        if group_markers:
            view.blocks.append(Box("group:" + identity, title, []))
            title = ""
        view.blocks.append(Graph(boxes, relations, title, legend))
        if not any(edge.inferred for edge in relations) and any(
                edge.inferred and (edge.origin in ids or edge.target in ids) for edge in all_edges):
            view.text(legend)


def project_map(view: View, inventory: dict, documents: list[dict], model: dict) -> None:
    project = model["project_view"]
    numbers, known = _numbers(inventory), {doc["id"]: doc for doc in inventory["documents"]}
    selected = {doc["id"] for doc in documents}
    boxes = []
    for node in project["nodes"]:
        references = {ref["document"] for ref in node.get("sources", [])} | set(node.get("members", []))
        title = node["label"]
        if node.get("members"):
            title += f" ({_file_count(len(node['members']))})"
        if references and not references & selected:
            title += " [context]"
        body = [node["summary"]] if node.get("summary") else []
        if node.get("members"):
            body.append("Member files appear in the file key; continue the view if needed.")
        elif references:
            body.append("Files: " + " ".join(f"[{numbers[ref]}]" for ref in sorted(references, key=numbers.get)))
        boxes.append(Box(node["id"], title, body))
    view.blocks.append(Graph(boxes, edges(project.get("relationships", []), {box.identity for box in boxes})))
    for identity in project.get("unresolved_documents", []):
        document = known[identity]
        view.blocks.append(Box("unresolved:" + identity, f"[{numbers[identity]}] {document['path'].split('/')[-1]} [unresolved]",
                               ["The project-level meaning of this document is unresolved."]))


def overview_view(inventory: dict, model: dict | None = None, detailed: bool = False, width: int = 80,
                  *, omit_hint: bool = False) -> View:
    view = start_view(inventory, model, width)
    documents = _documents(inventory)
    view.text(f"Specification map ({_file_count(len(documents))})")
    if documents:
        if (model or {}).get("project_view") is not None:
            project_map(view, inventory, documents, model)
        else:
            view.text("Project relationships unresolved; showing the known document structure.")
            document_map(view, inventory, documents, model)
        file_key(view, inventory, documents)
    else:
        view.text("No specification files found in this scope. Select a Markdown file explicitly, or check the project path.")
    file_key(view, inventory, _documents(inventory, inventory.get("context", [])), context=True)
    if detailed:
        interpreted = _model_documents(model)
        for document in documents:
            body = ["Purpose: " + _purpose(document, interpreted.get(document["id"]))]
            for item in _items(document, interpreted.get(document["id"])):
                body.append(item.get("label", "Meaning unspecified") + (" [unresolved]" if item.get("kind") in {"unknown", "unresolved"} else ""))
                body.extend(_item_notes(document, item))
                body.extend("Source: " + ref for ref in _source_refs(document, item))
            view.blocks.append(Box(document["id"], f"File [{_numbers(inventory)[document['id']]}]: {document['path']}", body))
    hint = "Use show <file number or path> to explore a file; add --detailed to expand it." if documents and not omit_hint else ""
    return finish_view(view, inventory, detailed, hint)


def content_graph(document: dict, interpreted: dict | None, number: int, detailed: bool) -> Graph:
    boxes = []
    for index, item in enumerate(_items(document, interpreted), 1):
        unresolved = item.get("kind") in {"unknown", "unresolved"}
        title = f"({index}) {item.get('label') or 'Meaning unspecified'}" + (" [unresolved]" if unresolved else "")
        body = [item["summary"]] if item.get("summary") else []
        if detailed:
            body.extend(note for note in _item_notes(document, item) if note not in body)
        refs = _source_refs(document, item)
        if not detailed:
            refs = [ref.split(" - ", 1)[0] for ref in refs]
        body.extend("Source: " + ref for ref in refs)
        boxes.append(Box(item["id"], title, body))
    kinds = {"tree": "Content hierarchy", "flow": "Behavior flow", "interaction": "Interactions", "rules": "Independent rules"}
    title = f"File [{number}]: {document['path'].split('/')[-1]} - " + kinds.get((interpreted or {}).get("layout", "tree"), "Content hierarchy")
    return Graph(boxes, edges((interpreted or {}).get("relationships", []), {box.identity for box in boxes}), title)


def show_view(inventory: dict, document_ids: list[str] | None = None, model: dict | None = None,
              detailed: bool = False, width: int = 80) -> View:
    view = start_view(inventory, model, width)
    documents = _documents(inventory, document_ids)
    if len(documents) > 1:
        document_map(view, inventory, documents, model)
    file_key(view, inventory, documents)
    file_key(view, inventory, _documents(inventory, inventory.get("context", [])), context=True)
    interpreted = _model_documents(model)
    for document in documents:
        interpretation = interpreted.get(document["id"])
        if interpretation is None:
            view.text("Interpretation unavailable: source sections remain unresolved. Detailed mode retains their exact wording.")
        graph = content_graph(document, interpretation, _numbers(inventory)[document["id"]], detailed)
        if graph.boxes:
            view.blocks.append(graph)
        else:
            view.blocks.append(Box(document["id"], f"File [{_numbers(inventory)[document['id']]}]: {document['path']}",
                                   ["No substantive content identified. Coverage unresolved."]))
    if not documents:
        view.text("No selected files found. Use overview to see available numbers and paths.")
    return finish_view(view, inventory, detailed)


def comparison_box(identity: str, row: dict, labels: dict, detailed: bool) -> Box:
    # Retain the established evidence wording; layout owns wrapping and borders.
    writer = _Writer(1_000_000)
    _comparison_row(writer, row, labels, detailed)
    title = writer.lines[0].removeprefix("+-- ")
    body = [line.removeprefix("|   ") for line in writer.lines[1:]]
    return Box(identity, title, body)


def changes_view(inventory: dict, comparison: dict, model: dict | None = None,
                 detailed: bool = False, width: int = 80) -> View:
    view = start_view(inventory, model, width)
    view.text("Basis: " + clean(comparison.get("basis") or
              "Workflow completion and verification reports; missing evidence remains unknown."))
    if not detailed:
        view.text("Full source wording is available with --detailed.")
    documents = _documents(inventory)
    rows_by_document: dict[str, list[dict]] = {}
    for row in comparison.get("rows", []):
        rows_by_document.setdefault(str(row.get("document", "")), []).append(row)
    markers, groups = {}, {}
    for document in documents:
        rows = rows_by_document.get(document["path"], rows_by_document.get(document["id"], []))
        if not rows or any(_active_change(row) for row in rows):
            changed = any(row.get("difference") not in {"unchanged", "documentation-only", "unresolved", "source-unavailable"} for row in rows)
            markers[document["id"]] = "[changed] " if changed else "[attention] "
            group = str(document.get("group") or "Other specifications")
            if changed:
                groups[group] = "[contains changes] "
            else:
                groups.setdefault(group, "[contains attention] ")
    document_map(view, inventory, documents, model, markers, groups)
    file_key(view, inventory, documents)
    file_key(view, inventory, _documents(inventory, inventory.get("context", [])), context=True)
    view.text("[changed] marks a requested difference; [attention] marks uncertain or incomplete evidence. Their groups carry [contains changes] or [contains attention].")
    interpreted = _model_documents(model)
    for document in documents:
        rows = rows_by_document.get(document["path"], rows_by_document.get(document["id"], []))
        labels = {item["id"]: item.get("label") for item in _items(document, interpreted.get(document["id"]))}
        title = f"File [{_numbers(inventory)[document['id']]}]: {document['path'].split('/')[-1]}"
        view.text(title)
        if not rows:
            view.blocks.append(Box(document["id"], "[attention] Implementation unknown",
                                   ["No applicable requirement evidence."]))
        for index, row in enumerate(rows):
            view.blocks.append(comparison_box(f"{document['id']}:evidence:{index}", row, labels, detailed))
    known = {value for document in inventory.get("documents", []) for value in (document["id"], document["path"])}
    missing = {path: rows for path, rows in rows_by_document.items() if path not in known}
    if missing:
        view.blocks.append(Box("historical", "[contains attention] Historical source correspondence unresolved",
                               [f"{_file_count(len(missing))}. Earlier paths are unavailable in the current inventory. A missing or moved file does not establish a behavior-removal request."]))
        for path, rows in missing.items():
            view.blocks.append(Box("historical:" + path, "[source unavailable] " + (path or "Unidentified historical file"),
                                   [f"{len(rows)} requirement" + ("" if len(rows) == 1 else "s") + " with unresolved correspondence.",
                                    "Source disclosure: not located in the current inventory; it may have moved or become unavailable. Implementation and requested removal remain unconfirmed."]))
            for index, row in enumerate(rows):
                view.blocks.append(comparison_box(f"historical:{path}:{index}", row, {}, detailed))
    for warning in comparison.get("warnings", []):
        view.text("Unresolved: " + clean(warning))
    hint = "Explore further: changes --detailed for expanded evidence; changes --check-code to inspect relevant code."
    if set(inventory.get("scope", [])) != {doc["id"] for doc in inventory.get("documents", [])}:
        hint += " Include the same selected paths to keep this local scope."
    return finish_view(view, inventory, detailed, hint)
