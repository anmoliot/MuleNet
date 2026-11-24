"""Purged temporal splits and whole-component entity isolation."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

import networkx as nx

from .graph import canonical_events
from .labels import Example, materialize
from .schema import Account, FeatureConfig, Transaction


@dataclass(frozen=True)
class Split:
    train: tuple[Example, ...]
    val: tuple[Example, ...]
    test: tuple[Example, ...]
    purged: tuple[Example, ...] = ()


def temporal_split(rows: Iterable[Example], train_end: int, val_end: int) -> Split:
    if not 0 < train_end < val_end:
        raise ValueError("Require train_end < val_end")
    train, val, test, purged = [], [], [], []
    for row in rows:
        if row.label_end < train_end:
            train.append(row)
        elif row.as_of >= train_end and row.label_end < val_end:
            val.append(row)
        elif row.as_of >= val_end:
            test.append(row)
        else:
            purged.append(row)
    if not all((train, val, test)):
        raise ValueError("Temporal split needs nonempty train, validation and test after purging")
    result = Split(tuple(train), tuple(val), tuple(test), tuple(purged))
    assert_no_label_leakage(result)
    return result


def entity_partitions(events: Iterable[Transaction], seed: int = 42) -> dict[str, str]:
    graph = nx.Graph()
    ring_members: dict[str, str] = {}
    for event in canonical_events(events):
        graph.add_edge(event.source, event.target)
        if event.ring_id:
            prior = ring_members.setdefault(event.ring_id, event.source)
            graph.add_edge(prior, event.source)
    components = sorted((tuple(sorted(c)) for c in nx.connected_components(graph)))
    if len(components) < 3:
        raise ValueError("Need independent components/rings for entity-disjoint train, validation, test")
    random.Random(seed).shuffle(components)
    train_end = max(1, min(len(components) - 2, int(len(components) * 0.6)))
    val_end = max(train_end + 1, min(len(components) - 1, int(len(components) * 0.8)))
    return {node: ("train" if i < train_end else "val" if i < val_end else "test") for i, comp in enumerate(components) for node in comp}


def partition_events(events: Iterable[Transaction], assignments: dict[str, str], partition: str) -> tuple[Transaction, ...]:
    if partition not in {"train", "val", "test"}:
        raise ValueError("Unknown partition")
    return tuple(e for e in canonical_events(events) if assignments[e.source] == assignments[e.target] == partition)


def entity_split(
    events: Iterable[Transaction], points: Iterable[tuple[str, int]], horizon: int,
    complete_through: int, config: FeatureConfig = FeatureConfig(),
    accounts: Iterable[Account] = (), seed: int = 42,
) -> Split:
    ordered = canonical_events(events)
    assignments = entity_partitions(ordered, seed)
    point_list, registry = list(points), tuple(accounts)
    if any(account not in assignments for account, _ in point_list):
        raise ValueError("Unknown account in entity-split points")
    groups = []
    for name in ("train", "val", "test"):
        selected = partition_events(ordered, assignments, name)
        selected_points = [(account, ts) for account, ts in point_list if assignments[account] == name]
        selected_accounts = [account for account in registry if assignments.get(account.account_id) == name]
        groups.append(tuple(materialize(selected, selected_points, horizon, complete_through, config, selected_accounts)))
    if not all(groups):
        raise ValueError("Entity split needs nonempty training, validation and test examples")
    result = Split(groups[0], groups[1], groups[2])
    assert_entity_isolation(result)
    assert_no_label_leakage(result)
    return result


def assert_entity_isolation(split: Split) -> None:
    groups = [{row.account_id for row in rows} for rows in (split.train, split.val, split.test)]
    if groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2]:
        raise ValueError("Account appears in multiple entity partitions")
    # Entity-disjoint features must also be materialized from isolated edges.
    dependencies = [{e for row in rows for e in row.feature_event_ids + row.label_event_ids} for rows in (split.train, split.val, split.test)]
    if dependencies[0] & dependencies[1] or dependencies[0] & dependencies[2] or dependencies[1] & dependencies[2]:
        raise ValueError("Edge appears in multiple entity partitions")


def assert_no_label_leakage(split: Split) -> None:
    for rows in (split.train, split.val, split.test):
        for row in rows:
            if set(row.feature_event_ids) & set(row.label_event_ids):
                raise ValueError("An example observes its own future label-window edge")
    train_ids = {e for row in split.train for e in row.feature_event_ids}
    heldout_labels = {e for row in split.val + split.test for e in row.label_event_ids}
    if train_ids & heldout_labels:
        raise ValueError("Held-out label-window edge is present in training features")
