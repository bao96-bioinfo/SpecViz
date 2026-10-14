"""Bounded compact topology, independent of explanation length.

Small maps use separate connector lanes. An x is an explicitly nonjoining
crossing; a + turns a connector without joining unrelated edges. Large maps use a binary
layout hierarchy, followed by boundary maps. No routing search is performed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .text import display_width


@dataclass
class MapBlock:
    lines: list[str]
    title: str
    nodes: tuple[str, ...]
    edges: tuple[int, ...]
    documents: tuple[str, ...] = ()

    def draw(self, width):
        if any(display_width(line) > width for line in self.lines):
            raise ValueError("Structural map exceeds its column budget")
        return self.lines


def _pair(labels, edges, width):
    """At most two boxes; opposite arrows have separate, visible routes."""
    from .layout import Box

    size = min(max(len(label) for label in labels) + 4, (width - 4) // 2)
    drawings = [Box(str(i), label).draw(size) for i, label in enumerate(labels)]
    if len(labels) == 1:
        return drawings[0]
    height = max(map(len, drawings))
    drawings = [Box(str(i), label).draw(size, height) for i, label in enumerate(labels)]
    forward = any(a == 0 and b == 1 for a, b in edges)
    reverse = any(a == 1 and b == 0 for a, b in edges)
    lines = [
        left
        + (
            "--->"
            if forward and y == 1
            else "<---"
            if reverse and not forward and y == 1
            else "    "
        )
        + right
        for y, (left, right) in enumerate(zip(*drawings))
    ]
    if forward and reverse:
        left, right = size // 2, size + 4 + size // 2
        lines += [
            " " * left + "^" + " " * (right - left - 1) + "|",
            " " * left + "+" + "-" * (right - left - 1) + "+",
        ]
    return lines


def _lanes(labels, edges, width):
    """Separate side lanes make arbitrary feedback and joins traceable."""
    from .layout import Box

    size = max(len(label) for label in labels) + 4
    if size + 4 + 3 * len(edges) > width:
        return None
    positions, ports, row = {}, {}, 0
    for node, label in enumerate(labels):
        attached = [
            (index, side)
            for index, (origin, target) in enumerate(edges)
            for side, endpoint in (("out", origin), ("in", target))
            if endpoint == node
        ]
        height = 3 + len(attached)
        positions[node] = (row, height)
        for offset, (index, side) in enumerate(attached, 2):
            ports[index, side] = row + offset
        row += height + 1
    cells = [[" "] * width for _ in range(row - 1)]
    wires = {}

    def segment(x1, y1, x2, y2, number):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                wires.setdefault((x, y), []).append((number, "|" if x1 == x2 else "-"))

    for index, (origin, target) in enumerate(edges):
        lane = size + 3 + index * 3
        start, end = ports[index, "out"], ports[index, "in"]
        segment(size, start, lane, start, index)
        segment(lane, start, lane, end, index)
        segment(size, end, lane, end, index)
    for (x, y), entries in wires.items():
        directions = {entry[1] for entry in entries}
        cells[y][x] = (
            next(iter(directions))
            if len(directions) == 1
            else "+"
            if len({entry[0] for entry in entries}) == 1
            else "x"
        )
    for index in range(len(edges)):
        cells[ports[index, "in"]][size] = "<"
    for index, label in enumerate(labels):
        top, height = positions[index]
        for dy, line in enumerate(Box(str(index), label).draw(size, height)):
            cells[top + dy][:size] = list(line)
    return ["".join(line).rstrip() for line in cells]


def _row(labels, edges, width):
    """Use a compact horizontal row when every connector has its own port."""
    size = max(len(label) for label in labels) + 2
    if len(labels) * (size + 3) - 3 > width:
        return None
    ports = {}
    for node in range(len(labels)):
        attached = [
            (index, side)
            for index, (a, b) in enumerate(edges)
            for side, endpoint in (("out", a), ("in", b))
            if endpoint == node
        ]
        if len(attached) > size - 2:
            return None
        for offset, (index, side) in enumerate(attached, 1):
            ports[index, side] = node * (size + 3) + offset
    top = 2 * len(edges) + 1 if edges else 0
    cells = [[" "] * width for _ in range(top + 3)]
    wires = {}

    def segment(x1, y1, x2, y2, number):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                wires.setdefault((x, y), []).append((number, "|" if x1 == x2 else "-"))

    # Long connections occupy the outer lanes; short ones stay near their boxes.
    order = sorted(
        range(len(edges)), key=lambda i: (-abs(edges[i][1] - edges[i][0]), i)
    )
    for lane, index in enumerate(order):
        start, end = ports[index, "out"], ports[index, "in"]
        y = lane * 2
        segment(start, top - 1, start, y, index)
        segment(start, y, end, y, index)
        segment(end, y, end, top - 1, index)
    for (x, y), entries in wires.items():
        directions = {e[1] for e in entries}
        cells[y][x] = (
            next(iter(directions))
            if len(directions) == 1
            else "+"
            if len({e[0] for e in entries}) == 1
            else "x"
        )
    for index in range(len(edges)):
        cells[top - 1][ports[index, "in"]] = "v"
    for node, label in enumerate(labels):
        x = node * (size + 3)
        border = "+" + "-" * (size - 2) + "+"
        for offset, line in enumerate(
            (border, "|" + label.ljust(size - 2) + "|", border)
        ):
            cells[top + offset][x : x + size] = list(line)
    return ["".join(line).rstrip() for line in cells]


def _spine(labels, edges, width):
    """A longest-path backbone with single-edge side inputs or outputs.

    This bounded special case keeps ordinary processes readable without the
    parallel wire lanes needed for arbitrary graphs. Refuse unfamiliar shapes.
    """
    from .layout import Box

    remaining = set(range(len(labels)))
    order = []
    while remaining:
        ready = sorted(
            n for n in remaining if not any(b == n and a in remaining for a, b in edges)
        )
        if not ready:
            return None
        order.extend(ready)
        remaining.difference_update(ready)
    paths = {}
    for node in order:
        parents = [paths[a] for a, b in edges if b == node]
        paths[node] = max(parents, key=len, default=[]) + [node]
    spine = max(paths.values(), key=len, default=[])
    size = max(map(len, labels), default=0) + 4
    if len(spine) < 3 or len(spine) * (size + 6) - 6 > width:
        return None
    positions = {n: i for i, n in enumerate(spine)}
    sides = {}
    for node in range(len(labels)):
        if node in positions:
            continue
        attached = [(a, b) for a, b in edges if node in (a, b)]
        if len(attached) != 1:
            return None
        a, b = attached[0]
        parent = b if a == node else a
        if parent not in positions or parent in sides:
            return None
        sides[parent] = node
    ordinary = set(zip(spine, spine[1:]))
    extras = [
        (i, a, b)
        for i, (a, b) in enumerate(edges)
        if (a, b) not in ordinary and a in positions and b in positions
    ]
    top_edges = [
        entry for entry in extras if entry[1] not in sides and entry[2] not in sides
    ]
    bottom_edges = [entry for entry in extras if entry not in top_edges]
    side_y = 2 * len(top_edges)
    main_y = side_y + 5 if sides else 2 * len(top_edges) + 1
    height = main_y + 3 + (2 * len(bottom_edges) + 1 if bottom_edges else 0)
    cells = [[" "] * width for _ in range(height)]
    wires = {}

    def segment(x1, y1, x2, y2, index):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            for x in range(min(x1, x2), max(x1, x2) + 1):
                wires.setdefault((x, y), []).append((index, "|" if x1 == x2 else "-"))

    arrows = []
    for index, (a, b) in enumerate(edges):
        if (a, b) in ordinary:
            start = positions[a] * (size + 6) + size
            end = positions[b] * (size + 6) - 1
            segment(start, main_y + 1, end, main_y + 1, index)
            arrows.append((end, main_y + 1, ">"))
        elif a not in positions or b not in positions:
            parent = b if a not in positions else a
            x = positions[parent] * (size + 6) + size // 2
            segment(x, side_y + 3, x, main_y - 1, index)
            arrows.append((x, main_y - 1, "v") if b == parent else (x, side_y + 3, "^"))
    for entries, above in ((top_edges, True), (bottom_edges, False)):
        used = {}
        for lane, (index, a, b) in enumerate(entries):
            ports = []
            for node in (a, b):
                offset = used.get(node, 0) + 1
                used[node] = offset
                if offset > size - 2:
                    return None
                ports.append(positions[node] * (size + 6) + offset)
            start, end = ports
            y = lane * 2 if above else main_y + 4 + lane * 2
            near = main_y - 1 if above else main_y + 3
            segment(start, near, start, y, index)
            segment(start, y, end, y, index)
            segment(end, y, end, near, index)
            arrows.append((end, near, "v" if above else "^"))
    for (x, y), entries in wires.items():
        chars = {entry[1] for entry in entries}
        cells[y][x] = (
            next(iter(chars))
            if len(chars) == 1
            else "+"
            if len({e[0] for e in entries}) == 1
            else "x"
        )
    for x, y, char in arrows:
        cells[y][x] = char
    for node, column in positions.items():
        for actual, y in [(node, main_y)] + (
            [(sides[node], side_y)] if node in sides else []
        ):
            x = column * (size + 6)
            for offset, line in enumerate(Box(str(actual), labels[actual]).draw(size)):
                cells[y + offset][x : x + size] = list(line)
    lines = ["".join(line).rstrip() for line in cells]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def compact_maps(graph, width, budget):
    """Return maps with coverage metadata; O((N+E) log N + E) bounded work.

    A routing attempt is limited to 12 nodes and 16 edges. Binary partitions
    reduce all larger inputs; boundary maps draw each crossing edge exactly
    once after the counted root structure. Every leaf uses original identities.
    """
    from .layout import TextBlock

    keys = {box.identity: f"Node {i}" for i, box in enumerate(graph.boxes, 1)}
    edges = list(enumerate(graph.edges, 1))
    maps = []
    group_number = 0

    def route(ids, relations, labels=None):
        if len(ids) > 12 or len(relations) > 16:
            return None
        labels = labels or [keys[i] for i in ids]
        positions = {identity: index for index, identity in enumerate(ids)}
        pairs = [(positions[e.origin], positions[e.target]) for _, e in relations]
        if len(ids) <= 2 and all(a != b for a, b in pairs):
            lines = _pair(labels, pairs, width)
        else:
            lines = _spine(labels, pairs, width)
            if lines is None or len(lines) > budget:
                lines = _row(labels, pairs, width)
            if lines is None or len(lines) > budget:
                lines = _lanes(labels, pairs, width)
        return lines if lines is not None and len(lines) <= budget else None

    def emit(ids, relations, title, labels=None):
        lines = route(ids, relations, labels)
        if lines is None:
            return False
        maps.append(MapBlock(lines, title, tuple(ids), tuple(i for i, _ in relations)))
        return True

    def partition(ids, relations, title):
        nonlocal group_number
        if emit(ids, relations, title):
            return
        if len(ids) == 1:
            # Only a self-edge can exceed the small routing budget. Draw it
            # independently; duplicates retain this same source identity.
            emit(ids, [], title)
            for edge in relations:
                if not emit(ids, [edge], title + " feedback"):
                    raise ValueError(
                        "A structural feedback map cannot fit the supported budget"
                    )
            return
        midpoint = (len(ids) + 1) // 2
        halves = [ids[:midpoint], ids[midpoint:]]
        group_number += 1
        left = f"G{group_number}"
        group_number += 1
        right = f"G{group_number}"
        owners = {
            identity: index for index, part in enumerate(halves) for identity in part
        }
        cross = [(i, e) for i, e in relations if owners[e.origin] != owners[e.target]]
        pairs = list(
            dict.fromkeys((owners[e.origin], owners[e.target]) for _, e in cross)
        )
        labels = [
            f"{label}\n{len(part)} nodes" for label, part in zip((left, right), halves)
        ]
        lines = _pair(labels, pairs, width)
        # Labels/counts are bounded by the caller's supported minimum width.
        if len(lines) > budget:
            labels = [left, right]
            lines = _pair(labels, pairs, width)
        maps.append(MapBlock(lines, title, tuple(ids), tuple(i for i, _ in cross)))
        maps.append(
            TextBlock(
                f"{left}: layout group, {len(halves[0])} nodes; {right}: layout group, {len(halves[1])} nodes. "
                "Arrows summarize cross-group connections; expansions retain every endpoint."
            )
        )
        for label, part in zip((left, right), halves):
            members = set(part)
            maps.append(
                TextBlock(label + " members: " + ", ".join(keys[i] for i in part))
            )
            partition(
                part,
                [
                    (i, e)
                    for i, e in relations
                    if e.origin in members and e.target in members
                ],
                label + " expansion",
            )
        # Boundary references are structural expansions, not replacement prose.
        for i, e in cross:
            emit(
                [e.origin, e.target],
                [(i, e)],
                f"Boundary E{i}: repeated node keys refer to the same components",
            )

    ids = [box.identity for box in graph.boxes]
    partition(ids, edges, "Overall structure")
    return maps, keys


def presentation(graph, width, budget):
    from .layout import Box, TextBlock

    maps, keys = compact_maps(graph, width, budget)
    units = []
    if graph.title:
        units.append(TextBlock(graph.title))
    crossing = any(
        "x" in line
        for block in maps
        if isinstance(block, MapBlock)
        for line in block.lines
    )
    units.append(
        TextBlock(
            "Overall structure. Arrowheads show direction."
            + (" x is a crossing, not a junction." if crossing else "")
        )
    )
    for block in maps:
        if isinstance(block, MapBlock) and block.title != "Overall structure":
            units.append(TextBlock(block.title))
        units.append(block)
    for box in graph.boxes:
        units.append(TextBlock(f"{keys[box.identity]}: {box.title}"))
    for i, edge in enumerate(graph.edges, 1):
        units.append(
            TextBlock(
                f"E{i}: {keys[edge.origin]} -> {keys[edge.target]} ({edge.kind}): {edge.caption}"
            )
        )
    if any(e.inferred for e in graph.edges):
        units.append(TextBlock(graph.inference_note))
    units.append(TextBlock("Component details"))
    for panel in graph.panels():
        units.append(
            Box(
                panel.identity,
                keys[panel.identity] + ": " + panel.title,
                panel.body,
                panel.documents,
            )
        )
    return units
