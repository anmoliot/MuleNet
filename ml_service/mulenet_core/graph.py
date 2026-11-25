"""Lossless transaction graphs with explicit event-time/resource bounds."""

from __future__ import annotations

from collections.abc import Iterable

import networkx as nx

from .schema import FeatureConfig, Transaction


class FeatureBudgetExceeded(ValueError):
    """Refuse an oversized snapshot instead of silently changing its topology."""


def canonical_events(events: Iterable[Transaction]) -> tuple[Transaction, ...]:
    by_id: dict[str, Transaction] = {}
    for event in events:
        previous = by_id.get(event.transaction_id)
        if previous is not None and previous != event:
            raise ValueError(f"Conflicting transaction id: {event.transaction_id}")
        by_id[event.transaction_id] = event
    return tuple(sorted(by_id.values(), key=lambda e: (e.ts, e.transaction_id)))


def window_events(
    events: Iterable[Transaction], as_of: int, seconds: int, currency: str
) -> tuple[Transaction, ...]:
    return tuple(e for e in canonical_events(events) if as_of - seconds < e.ts <= as_of and e.currency == currency)


def transaction_graph(events: Iterable[Transaction], config: FeatureConfig) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for event in events:
        graph.add_edge(event.source, event.target, key=event.transaction_id, amount=event.amount, ts=event.ts)
        if graph.number_of_nodes() > config.max_graph_nodes or graph.number_of_edges() > config.max_graph_edges:
            raise FeatureBudgetExceeded("Snapshot exceeds graph bounds; partition explicitly before extraction")
    return graph


def amount_graph(graph: nx.MultiDiGraph) -> nx.DiGraph:
    result = nx.DiGraph()
    result.add_nodes_from(sorted(graph.nodes))
    for source, target, data in graph.edges(data=True):
        if result.has_edge(source, target):
            result[source][target]["weight"] += data["amount"]
        else:
            result.add_edge(source, target, weight=data["amount"])
    return result


def hop_flows(graph: nx.DiGraph, account_id: str, incoming: bool) -> tuple[float, float, float]:
    if account_id not in graph:
        return (0.0, 0.0, 0.0)
    view = graph.reverse(copy=False) if incoming else graph
    distances = nx.single_source_shortest_path_length(view, account_id, cutoff=2)
    # Each traversed edge is counted once, at its source's minimum directed distance.
    return tuple(
        float(sum(data["weight"] for u, _, data in view.edges(data=True) if distances.get(u) == depth))
        for depth in range(3)
    )  # type: ignore[return-value]


def bounded_cycle_counts(graph: nx.DiGraph, config: FeatureConfig) -> dict[str, int]:
    counts = dict.fromkeys(graph.nodes, 0)
    for index, cycle in enumerate(nx.simple_cycles(graph, length_bound=5)):
        if index >= config.max_cycles:
            raise FeatureBudgetExceeded("Cycle enumeration budget exceeded")
        for node in cycle:
            counts[node] += 1
    return counts
