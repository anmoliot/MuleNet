from dataclasses import replace

import pytest
from mulenet_core.labels import future_label, materialize
from mulenet_core.schema import Transaction
from mulenet_core.splits import (
    Split,
    assert_entity_isolation,
    assert_no_label_leakage,
    entity_partitions,
    entity_split,
    partition_events,
    temporal_split,
)


def events():
    return tuple(
        Transaction(
            transaction_id=f"{group}-{ts}",
            source=f"a{group}",
            target=f"b{group}",
            ts=ts,
            amount=10.0,
            fraud=ts % 30 == 0,
            ring_id=str(group),
        )
        for group in range(6)
        for ts in range(10, 101, 10)
    )


def test_temporal_split_purges_overlapping_windows():
    data = events()
    points = [("a0", ts) for ts in range(10, 91, 10)]
    rows = materialize(data, points, 10, 100)
    split = temporal_split(rows, 40, 70)
    assert all(row.label_end < 40 for row in split.train)
    assert all(40 <= row.as_of < row.label_end < 70 for row in split.val)
    assert all(row.as_of >= 70 for row in split.test)
    assert split.purged
    assert_no_label_leakage(split)
    indexed = {e.transaction_id: e for e in data}
    for row in rows:
        assert all(indexed[key].ts <= row.as_of for key in row.feature_event_ids)
        assert all(row.as_of < indexed[key].ts <= row.label_end for key in row.label_event_ids)


def test_entity_disjoint_components_and_ring_union():
    data = events()
    assignments = entity_partitions(data)
    assert assignments == entity_partitions(reversed(data))
    groups = []
    for name in ("train", "val", "test"):
        isolated = partition_events(data, assignments, name)
        nodes = sorted({e.source for e in isolated} | {e.target for e in isolated})
        groups.append(tuple(materialize(isolated, [(node, 50) for node in nodes], 10, 100)))
    split = Split(*groups)
    assert_entity_isolation(split)
    assert_no_label_leakage(split)
    assert all(assignments[e.source] == assignments[e.target] for e in data)
    direct = entity_split(data, [(f"a{i}", 50) for i in range(6)], 10, 100)
    assert_entity_isolation(direct)
    with pytest.raises(ValueError, match="independent"):
        entity_partitions([e.model_copy(update={"ring_id": "same-ring"}) for e in data])


def test_leakage_checks_reject_injected_test_edges_and_entity_overlap():
    row = materialize(events(), [("a0", 20)], 10, 100)[0]
    bad = replace(row, feature_event_ids=row.feature_event_ids + row.label_event_ids)
    with pytest.raises(ValueError, match="future"):
        assert_no_label_leakage(Split((bad,), (), ()))
    with pytest.raises(ValueError, match="Account"):
        assert_entity_isolation(Split((row,), (), (row,)))
    with pytest.raises(ValueError, match="complete"):
        future_label(events(), "a0", 95, 10, 100)
    label, ids = future_label(events(), "a0", 20, 10, 100)
    assert label == 1 and ids == ("0-30",)
    assert future_label(events(), "a0", 30, 1, 100) == (0, ())
    unknown = Transaction(transaction_id="unknown", source="a", target="b", ts=50, amount=1.0)
    with pytest.raises(ValueError, match="Unknown future labels"):
        future_label([unknown], "a", 40, 10, 100)
