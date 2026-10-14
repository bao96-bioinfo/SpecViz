"""Paginate semantic blocks, never slice completed diagram geometry."""
from __future__ import annotations

from dataclasses import dataclass, field

from .layout import Box, Graph, TextBlock, View, pad, prose
from .structure import MapBlock


@dataclass
class Page:
    text: str
    documents: list[str] = field(default_factory=list)
    section: str = "view notes"


def paginate(view: View, max_lines: int = 100) -> list[Page]:
    if max_lines < 12:
        raise ValueError("Structured views require at least 12 lines per page")
    # Four lines are reserved for the part header, separation and remainder notice.
    budget, width = max_lines - 4, view.width
    pages, lines, documents = [], [], []
    prior_context = ""
    section = "view notes"
    page_section = section

    def flush():
        nonlocal lines, documents, prior_context
        if lines:
            pages.append(Page("\n".join(lines).rstrip(), list(dict.fromkeys(documents)), page_section))
        lines, documents, prior_context = [], [], ""

    def put(chunk: list[str], refs: tuple[str, ...] = (), context: str = ""):
        nonlocal prior_context, page_section
        heading = prose(context, width) if context and (context != prior_context or
                  len(prose(context, width)) + len(chunk) > budget) else []
        separator = [""] if lines and (not context or context != prior_context) else []
        if len(lines) + len(separator) + len(heading) + len(chunk) > budget:
            flush()
            heading = prose(context, width) if context else []
            separator = []
        # Very long directory prefixes/keys remain complete across named parts.
        if not lines:
            page_section = section
        whole = heading + chunk
        while len(whole) > budget:
            lines.extend(whole[:budget])
            documents.extend(refs)
            flush()
            whole = whole[budget:]
        lines.extend(separator + whole)
        documents.extend(refs)
        prior_context = context

    def box(block: Box, key: str):
        nonlocal section
        if lines and len(lines) + len(block.draw(width)) + 1 > budget:
            flush()
        section = key
        drawn = block.draw(width)
        if len(drawn) <= budget:
            put(drawn, block.documents)
            return
        content = block.content(width)
        label = prose(key + " (continued)", width - 4)
        capacity = budget - len(label) - 2
        border = "+" + "-" * (width - 2) + "+"
        for offset in range(0, len(content), capacity):
            header = prose(key + (" (start)" if not offset else " (continued)"), width - 4)
            chunk = header + content[offset:offset + capacity]
            put([border] + ["| " + pad(line, width - 4) + " |" for line in chunk] + [border], block.documents)

    box_index = 0
    for block in view.presentation(budget):
        if isinstance(block, MapBlock):
            section = block.title
            drawn = block.draw(width)
            if len(drawn) > budget:
                raise ValueError("Structural map exceeds page budget")
            put(drawn, block.documents)
        elif isinstance(block, Box):
            box_index += 1
            box(block, block.title.split(":", 1)[0] if block.title.startswith(("Node ", "Diagram ")) else f"Panel {box_index}")
        else:
            section = "file keys" if block.documents else "view notes"
            put(block.draw(width), block.documents, block.context)
    flush()
    if not pages:
        return [Page("")]
    if len(pages) == 1:
        pages[0].text += "\n"
        return pages
    for index, page in enumerate(pages, 1):
        remaining = len(pages) - index
        # Keep continuation notices bounded too (including narrow destinations).
        notice = "Next: " + pages[index].section if remaining else "End of this view."
        notice = prose(notice, width)[0]
        page.text = (f"View part {index}/{len(pages)}\n\n" + page.text + "\n\n" + notice + "\n")
    return pages
