"""Future-only labels and auditable materialization dependencies."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from collections import defaultdict

from .features import FeatureSnapshot, extract_features
from .graph import canonical_events
from .schema import Account, FeatureConfig, Transaction


@dataclass(frozen=True)
class Example:
    account_id: str
    as_of: int
    label_end: int
    label: int
    features: dict[str, float]
    feature_event_ids: tuple[str, ...]
    label_event_ids: tuple[str, ...]


def future_label(events: Iterable[Transaction], account_id: str, as_of: int, horizon: int, complete_through: int, currency: str = "INR") -> tuple[int, tuple[str, ...]]:
    if horizon <= 0 or as_of + horizon > complete_through:
        raise ValueError("Positive horizon and complete future label window required")
    future = tuple(e for e in canonical_events(events) if as_of < e.ts <= as_of + horizon and e.currency == currency and account_id in (e.source, e.target))
    if any(e.fraud is None for e in future):
        raise ValueError("Unknown future labels cannot be treated as legitimate transactions")
    return int(any(e.fraud for e in future)), tuple(e.transaction_id for e in future)


def materialize(
    events: Iterable[Transaction], points: Iterable[tuple[str, int]], horizon: int,
    complete_through: int, config: FeatureConfig = FeatureConfig(), accounts: Iterable[Account] = (),
) -> list[Example]:
    ordered = canonical_events(events)
    registry = {a.account_id: a for a in accounts}
    by_account = defaultdict(list)
    for event in ordered:
        by_account[event.source].append(event)
        if event.target != event.source:
            by_account[event.target].append(event)
    snapshots, dependencies = {}, {}
    rows = []
    for account_id, as_of in points:
        label, label_ids = future_label(by_account[account_id], account_id, as_of, horizon, complete_through, config.currency)
        # Includes all graph dependencies, not just the focal account's edges.
        if as_of not in snapshots:
            snapshots[as_of] = FeatureSnapshot(ordered, as_of, config)
            dependencies[as_of] = tuple(e.transaction_id for e in snapshots[as_of].past)
        dependency_ids = dependencies[as_of]
        rows.append(Example(account_id, as_of, as_of + horizon, label,
                            extract_features(ordered, account_id, as_of, config, registry, _snapshot=snapshots[as_of]), dependency_ids, label_ids))
    return rows
