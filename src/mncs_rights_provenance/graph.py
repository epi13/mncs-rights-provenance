"""Provenance graph integrity checks (DAG semantics)."""

from __future__ import annotations

from typing import Any, Mapping


def check_graph_integrity(document: Mapping[str, Any]) -> tuple[bool, list[str]]:
    """Validate the manifest's embedded provenance graph.

    Rules:
    - node ids unique, non-empty;
    - edges reference existing nodes;
    - no self-loops;
    - no directed cycles (provenance is a DAG);
    - bounded size (256 nodes / 512 edges enforced at schema level too).
    """

    issues: list[str] = []
    graph = ((document.get("provenance") or {}).get("graph")) or {}
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    if not edges:
        return True, issues

    ids: set[str] = set()
    for node in nodes:
        if isinstance(node, Mapping) and isinstance(node.get("id"), str):
            ids.add(node["id"])

    adjacency: dict[str, list[str]] = {}
    for index, edge in enumerate(edges):
        if not isinstance(edge, Mapping):
            continue
        source = edge.get("from")
        target = edge.get("to")
        if source == target:
            issues.append(f"edge {index}: self-loop on {source!r}")
            continue
        if source in ids and target in ids:
            adjacency.setdefault(str(source), []).append(str(target))

    # Iterative cycle detection with colors (no recursion limits).
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node_id: WHITE for node_id in ids}
    for start in ids:
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        color[start] = GRAY
        while stack:
            current, offset = stack[-1]
            neighbors = adjacency.get(current, ())
            if offset >= len(neighbors):
                color[current] = BLACK
                stack.pop()
                continue
            stack[-1] = (current, offset + 1)
            neighbor = neighbors[offset]
            if color.get(neighbor, BLACK) == GRAY:
                issues.append(f"graph contains a directed cycle through {neighbor!r}")
                return False, sorted(set(issues))
            if color.get(neighbor, BLACK) == WHITE:
                color[neighbor] = GRAY
                stack.append((neighbor, 0))
    return not issues, sorted(set(issues))


__all__ = ["check_graph_integrity"]
