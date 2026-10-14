"""Measured ASCII diagrams. Geometry is never passed through prose wrapping."""

from __future__ import annotations

from dataclasses import dataclass, field

from .text import clean, display_width, wrap_text


def pad(value: str, columns: int) -> str:
    return value + " " * max(0, columns - display_width(value))


@dataclass
class Box:
    identity: str
    title: str
    body: list[str] = field(default_factory=list)
    documents: tuple[str, ...] = ()

    def content(self, width: int) -> list[str]:
        if width < 8:
            raise ValueError("A box requires at least 8 display columns")
        lines = wrap_text(self.title, width - 4)
        if self.body:
            lines.append("")
            for text in self.body:
                lines.extend(wrap_text(text, width - 4))
        return lines

    def draw(self, width: int, height: int | None = None) -> list[str]:
        lines = self.content(width)
        height = max(len(lines) + 2, height or 0)
        lines.extend([""] * (height - len(lines) - 2))
        border = "+" + "-" * (width - 2) + "+"
        return [border] + ["| " + pad(line, width - 4) + " |" for line in lines] + [border]


def prose(value: str, width: int) -> list[str]:
    """Produce terminal-safe prose without claiming it is a diagram."""
    return wrap_text(clean(value), width)


@dataclass(frozen=True)
class Edge:
    origin: str
    target: str
    label: str
    kind: str = "workflow"
    inferred: bool = False

    @property
    def caption(self) -> str:
        return clean(self.label or self.kind) + (" *" if self.inferred else "")


class _RoutingError(Exception):
    pass


class _Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.cells = [[" "] * width for _ in range(height)]
        self.wires: dict[tuple[int, int], list[Edge]] = {}

    def text(self, x: int, y: int, value: str) -> None:
        for char in value:
            size = display_width(char)
            if not size:
                if x:
                    previous = x - 1
                    while previous and self.cells[y][previous] == "":
                        previous -= 1
                    self.cells[y][previous] += char
                continue
            if x < 0 or x + size > self.width:
                raise _RoutingError()
            self.cells[y][x] = char
            for column in range(x + 1, x + size):
                self.cells[y][column] = ""
            x += size

    def wire(self, points: list[tuple[int, int]], edge: Edge) -> None:
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            if x1 != x2 and y1 != y2:
                raise _RoutingError()
            char = "|" if x1 == x2 else "-"
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    prior = self.wires.setdefault((x, y), [])
                    if any(p.origin != edge.origin and p.target != edge.target for p in prior):
                        raise _RoutingError()  # A crossing must not look like a junction.
                    prior.append(edge)
                    existing = self.cells[y][x]
                    self.cells[y][x] = char if existing in {" ", char} else "+"

    def lines(self) -> list[str]:
        return ["".join(row).rstrip() for row in self.cells]


@dataclass
class Graph:
    boxes: list[Box]
    edges: list[Edge] = field(default_factory=list)
    title: str = ""
    inference_note: str = "* Inferred relationship; see the stated connector meaning."

    @property
    def documents(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(doc for box in self.boxes for doc in box.documents))

    def _layers(self) -> list[list[Box]]:
        remaining = {box.identity: box for box in self.boxes}
        layers = []
        while remaining:
            ready = [box for box in remaining.values()
                     if not any(edge.target == box.identity and edge.origin in remaining for edge in self.edges)]
            if not ready:
                raise _RoutingError()  # Cycles use explicit return ports.
            layers.append(ready)
            for box in ready:
                del remaining[box.identity]
        return layers

    def _connected(self, width: int) -> list[str]:
        layers = self._layers()
        parallel = max((len(layer) for layer in layers), default=0)
        if parallel > 2 or (parallel == 2 and width < 52):
            raise _RoutingError()
        box_width = min(60, width) if parallel < 2 else (width - 4) // 2
        middle = (width - box_width) // 2
        positions: dict[str, tuple[int, int, int, int]] = {}
        layer_index: dict[str, int] = {}
        gap = max((len(wrap_text(edge.caption, box_width - 2)) for edge in self.edges), default=1) + 4
        y = 0
        for index, layer in enumerate(layers):
            height = max(len(box.content(box_width)) + 2 for box in layer)
            for column, box in enumerate(layer):
                x = column * (width - box_width) if len(layer) == 2 else middle
                if len(layer) == 1:
                    parents = {positions[e.origin][0] for e in self.edges
                               if e.target == box.identity and e.origin in positions}
                    if len(parents) == 1:
                        x = next(iter(parents))
                positions[box.identity] = (x, y, box_width, height)
                layer_index[box.identity] = index
            y += height + gap
        canvas = _Canvas(width, max(0, y - gap))
        labels = []
        for edge in self.edges:
            if edge.origin not in positions or edge.target not in positions:
                raise ValueError("Diagram edge refers to an unknown box")
            sx, sy, sw, sh = positions[edge.origin]
            tx, ty, tw, _ = positions[edge.target]
            start, end = sx + sw // 2, tx + tw // 2
            bottom = sy + sh - 1
            first_band = bottom + 2
            long_edge = layer_index[edge.target] > layer_index[edge.origin] + 1
            joins = sum(other.target == edge.target for other in self.edges) > 1
            lane = start if long_edge or joins else end
            if long_edge:
                for identity, (bx, by, bw, bh) in positions.items():
                    if identity not in {edge.origin, edge.target} and by > bottom and by < ty and bx <= lane < bx + bw:
                        raise _RoutingError()
            points = [(start, bottom), (start, first_band), (lane, first_band)]
            if long_edge or joins:
                points.extend([(lane, ty - 2), (end, ty - 2)])
            points.append((end, ty - 1))
            canvas.wire(points, edge)
            canvas.text(end, ty - 1, "v")
            caption_x = sx if long_edge or joins else tx
            labels.append((caption_x, first_band + 1, wrap_text(edge.caption, box_width - 2)))
        # Labels sit in deliberate gaps in their connector; surrounding stems
        # retain direction. Refuse unrelated labels rather than overwrite one.
        occupied: set[tuple[int, int]] = set()
        for x, row, words in labels:
            for offset, word in enumerate(words):
                left = x + max(0, (box_width - display_width(word)) // 2)
                cells = {(column, row + offset) for column in range(left, left + display_width(word))}
                if cells & occupied:
                    raise _RoutingError()
                occupied.update(cells)
                canvas.text(left, row + offset, word)
        for box in self.boxes:
            x, y, size, height = positions[box.identity]
            for offset, line in enumerate(box.draw(size, height)):
                canvas.text(x, y + offset, line)
        return canvas.lines()

    def panels(self) -> list[Box]:
        """Closed panels retain both endpoints when a graph must be separated."""
        panels = []
        keys = {box.identity: f"Node {index}" for index, box in enumerate(self.boxes, 1)}
        for box in self.boxes:
            incoming = [f"<-- {keys[edge.origin]}: {edge.caption}" for edge in self.edges if edge.target == box.identity]
            outgoing = [f"--> {keys[edge.target]}: {edge.caption}" for edge in self.edges if edge.origin == box.identity]
            panels.append(Box(box.identity, box.title, [f"({keys[box.identity]})"] + incoming + box.body + outgoing, box.documents))
        return panels

    def ports(self, width: int) -> list[str]:
        """Vertical panels with named endpoints for cycles or crowded graphs."""
        lines = []
        for panel in self.panels():
            if lines:
                lines.append("")
            lines.extend(panel.draw(width))
        return lines

    def presentation(self, width: int, budget: int = 96) -> list:
        if not self.boxes:
            return []
        identities = {box.identity for box in self.boxes}
        if len(identities) != len(self.boxes):
            raise ValueError("Diagram box identities must be unique")
        if any(edge.origin not in identities or edge.target not in identities for edge in self.edges):
            raise ValueError("Diagram edge refers to an unknown box")
        try:
            lines = self._connected(width)
        except _RoutingError:
            lines = None
        if lines is None or len(lines) + (len(prose(self.title, width)) + 1 if self.title else 0) + (len(prose(self.inference_note, width)) + 1 if any(e.inferred for e in self.edges) else 0) > budget:
            from .structure import presentation
            return presentation(self, width, budget)
        if self.title:
            lines = prose(self.title, width) + [""] + lines
        if any(edge.inferred for edge in self.edges):
            lines += [""] + prose(self.inference_note, width)
        from .structure import MapBlock
        return [MapBlock(lines, self.title or "Connected diagram", tuple(box.identity for box in self.boxes), tuple(range(1, len(self.edges) + 1)), self.documents)]

    def draw(self, width: int) -> list[str]:
        lines = []
        for block in self.presentation(width):
            if lines:
                lines.append("")
            lines.extend(block.draw(width))
        return lines


@dataclass
class TextBlock:
    text: str
    documents: tuple[str, ...] = ()
    context: str = ""

    def draw(self, width: int) -> list[str]:
        return prose(self.text, width)


@dataclass
class View:
    width: int = 80
    blocks: list[TextBlock | Box | Graph] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.width < 24:
            raise ValueError("Text views require a width of at least 24 columns.")

    def text(self, value: str, documents: tuple[str, ...] = (), context: str = "") -> None:
        self.blocks.append(TextBlock(value, documents, context))

    @property
    def documents(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(doc for block in self.blocks for doc in block.documents))

    def render(self) -> str:
        lines = []
        prior_context = ""
        for block in self.presentation():
            if lines and not (isinstance(block, TextBlock) and block.context and block.context == prior_context):
                lines.append("")
            context = block.context if isinstance(block, TextBlock) else ""
            if context and context != prior_context:
                lines.extend(prose(context, self.width))
            lines.extend(block.draw(self.width))
            prior_context = context
        return "\n".join(lines).rstrip() + "\n"

    def presentation(self, budget: int = 96) -> list:
        from .structure import MapBlock
        result, number = [], 0
        for block in self.blocks:
            if not isinstance(block, Graph):
                result.append(block)
                continue
            number += 1
            units = block.presentation(self.width, budget)
            if len(units) > 1:
                # Each graph owns its Node keys. Keep that namespace visible
                # when multiple file diagrams continue on separate pages.
                units[0].text = f"Diagram {number}: " + units[0].text
                for unit in units:
                    if isinstance(unit, MapBlock):
                        unit.title = f"Diagram {number}: " + unit.title
                    elif isinstance(unit, Box):
                        unit.title = f"Diagram {number}, " + unit.title
            result.extend(units)
        return result
