"""Reference feature semantics shared by online and offline materialization."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict, deque
from collections.abc import Iterable, Mapping
from functools import lru_cache

import networkx as nx

from .graph import amount_graph, bounded_cycle_counts, canonical_events, hop_flows, transaction_graph
from .schema import Account, FeatureConfig, Transaction, feature_names


@lru_cache(maxsize=4)
def _window_context(events: tuple[Transaction, ...], config: FeatureConfig):
    graph = amount_graph(transaction_graph(events, config))
    cycles = bounded_cycle_counts(graph, config)
    ranks = nx.pagerank(graph, alpha=0.85, weight="weight", tol=1e-12, max_iter=1000) if graph else {}
    return graph, cycles, ranks


def _entropy(incoming: list[Transaction]) -> float:
    weights: dict[str, float] = defaultdict(float)
    for event in incoming:
        weights[event.source] += event.amount
    total = sum(weights.values())
    if len(incoming) < 2 or total == 0:
        return 0.0
    return -sum((v / total) * math.log2(v / total) for v in weights.values() if v > 0) / math.log2(len(incoming))


def _dwell(events: list[Transaction], account_id: str) -> tuple[float, float]:
    receipts: deque[list[float]] = deque()
    durations: list[float] = []
    for event in events:
        # Same-time events are ordered by transaction id, never by fraud labels.
        if event.source == account_id:
            remainder = event.amount
            while receipts and remainder > 0:
                ts, available = receipts[0]
                matched = min(available, remainder)
                if matched > 0:
                    durations.append(event.ts - ts)
                remainder -= matched
                receipts[0][1] -= matched
                if receipts[0][1] <= 0:
                    receipts.popleft()
        if event.target == account_id and event.amount > 0:
            receipts.append([float(event.ts), event.amount])
    return (float(statistics.median(durations)), 1.0) if durations else (0.0, 0.0)


def _velocity(history: list[Transaction], count: int, as_of: int, window: int, history_seconds: int) -> float:
    buckets = max(1, (history_seconds - window) // window)
    counts = [0] * buckets
    start = as_of - window - buckets * window
    for event in history:
        if start < event.ts <= as_of - window:
            index = min((event.ts - start - 1) // window, buckets - 1)
            counts[index] += 1
    mean = statistics.fmean(counts)
    # Variance floor prevents infinite z-scores on dormant/new accounts.
    return (count - mean) / max(statistics.pstdev(counts), 1.0)


def _burstiness(events: list[Transaction]) -> float:
    times = [e.ts for e in events]
    intervals = [b - a for a, b in zip(times, times[1:])]
    if len(intervals) < 2:
        return 0.0
    mean = statistics.fmean(intervals)
    deviation = statistics.pstdev(intervals)
    return (deviation - mean) / (deviation + mean) if deviation + mean else 0.0


def _sharing(events: tuple[Transaction, ...], outgoing: list[Transaction], field: str, account_id: str) -> tuple[float, float]:
    identifiers = {getattr(e, field) for e in outgoing if getattr(e, field) is not None}
    peers = {e.source for e in events if getattr(e, field) in identifiers and e.source != account_id}
    return float(len(peers)), float(bool(identifiers))


def _balance_error(events: list[Transaction], account_id: str) -> tuple[float, float]:
    errors = []
    for event in events:
        if event.source == account_id and event.sender_balance_before is not None and event.sender_balance_after is not None:
            errors.append(abs(event.sender_balance_before - event.amount - event.sender_balance_after))
        if event.target == account_id and event.receiver_balance_before is not None and event.receiver_balance_after is not None:
            errors.append(abs(event.receiver_balance_before + event.amount - event.receiver_balance_after))
    return (math.log1p(statistics.median(errors)), 1.0) if errors else (0.0, 0.0)


def extract_features(
    events: Iterable[Transaction], account_id: str, as_of: int,
    config: FeatureConfig = FeatureConfig(), accounts: Mapping[str, Account] | None = None,
) -> dict[str, float]:
    if isinstance(as_of, bool) or not isinstance(as_of, int) or as_of < 0:
        raise ValueError("as_of must be a nonnegative integer UTC epoch second")
    if not account_id:
        raise ValueError("account_id is required")
    past = tuple(e for e in canonical_events(events) if e.ts <= as_of and e.currency == config.currency)
    related = [e for e in past if e.source == account_id or e.target == account_id]
    registry_account = (accounts or {}).get(account_id)
    if registry_account and registry_account.created_at > as_of:
        raise ValueError("Account is not created at this as-of time")
    if registry_account and related and registry_account.created_at > related[0].ts:
        raise ValueError("Transaction predates registered account creation")
    first_seen = registry_account.created_at if registry_account else (related[0].ts if related else as_of)
    result = {"account_age_seconds": float(as_of - first_seen), "account_age_known": float(registry_account is not None)}
    for window in config.windows:
        selected = tuple(e for e in past if e.ts > as_of - window)
        graph, cycles, ranks = _window_context(selected, config)
        incoming = [e for e in related if e.ts > as_of - window and e.target == account_id]
        outgoing = [e for e in related if e.ts > as_of - window and e.source == account_id]
        activity = [e for e in related if e.ts > as_of - window]
        sent, received = sum(e.amount for e in outgoing), sum(e.amount for e in incoming)
        in_peers, out_peers = {e.source for e in incoming}, {e.target for e in outgoing}
        known_payees = {e.target for e in related if e.source == account_id and e.ts <= as_of - window}
        dwell, dwell_observed = _dwell(activity, account_id)
        device_degree, device_observed = _sharing(selected, outgoing, "device_id", account_id)
        ip_degree, ip_observed = _sharing(selected, outgoing, "ip_address", account_id)
        balance_error, balance_observed = _balance_error(activity, account_id)
        values = {
            "in_degree": float(len(incoming)), "out_degree": float(len(outgoing)),
            "log_recv": math.log1p(received), "log_sent": math.log1p(sent),
            "unique_in": float(len(in_peers)), "unique_out": float(len(out_peers)),
            "counterparty_entropy": _entropy(incoming),
            "pass_through_ratio": min(sent, received) / max(received, 1e-12),
            "dwell_seconds": dwell, "dwell_observed": dwell_observed,
            "velocity_zscore": _velocity(related, len(activity), as_of, window, config.history_seconds),
            "new_payee_ratio": sum(e.target not in known_payees for e in outgoing) / max(len(outgoing), 1),
            "burstiness": _burstiness(activity),
            "round_amount_ratio": sum(math.isclose(e.amount % 1000, 0.0, abs_tol=1e-7) for e in outgoing) / max(len(outgoing), 1),
            "structuring_score": sum(config.structuring_threshold * 0.95 <= e.amount < config.structuring_threshold for e in outgoing) / max(len(outgoing), 1),
            "device_sharing_degree": device_degree, "ip_sharing_degree": ip_degree,
            "device_observed": device_observed, "ip_observed": ip_observed,
            "cycle_count": float(cycles.get(account_id, 0)),
            "clustering": float(nx.clustering(graph.to_undirected(), account_id)) if account_id in graph else 0.0,
            "pagerank": float(ranks.get(account_id, 0.0)),
            "fan_in_ratio": len(in_peers) / max(len(out_peers), 1),
            "fan_out_ratio": len(out_peers) / max(len(in_peers), 1),
            "balance_delta_error": balance_error, "balance_delta_observed": balance_observed,
        }
        for direction, incoming_flag in (("in", True), ("out", False)):
            for hop, flow in enumerate(hop_flows(graph, account_id, incoming_flag), 1):
                values[f"{direction}_flow_hop{hop}"] = math.log1p(flow)
        result.update({f"{key}_{window}s": float(value) for key, value in values.items()})
    if set(result) != set(feature_names(config)) or not all(math.isfinite(value) for value in result.values()):
        raise ValueError("Nonfinite or incomplete feature vector")
    return {name: result[name] for name in feature_names(config)}


class OnlineFeatureStore:
    """Reference event store; production bounded Redis storage belongs to Phase 4."""

    def __init__(self, config: FeatureConfig = FeatureConfig(), accounts: Iterable[Account] = ()) -> None:
        self.config = config
        self.accounts = {a.account_id: a for a in accounts}
        self._events: dict[str, Transaction] = {}

    def ingest(self, event: Transaction) -> None:
        old = self._events.get(event.transaction_id)
        if old is not None and old != event:
            raise ValueError(f"Conflicting transaction id: {event.transaction_id}")
        self._events[event.transaction_id] = event

    def snapshot(self, account_id: str, as_of: int) -> dict[str, float]:
        return extract_features(self._events.values(), account_id, as_of, self.config, self.accounts)
