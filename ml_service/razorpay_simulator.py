"""Synthetic Razorpay payout graph generator for MuleNet demos."""

from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple

import networkx as nx


def generate_razorpay_payout_graph(
    n_merchants: int = 3,
    n_beneficiaries: int = 50,
    mule_ratio: float = 0.15,
    n_clusters: int = 2,
    cluster_size_range: Tuple[int, int] = (3, 5),
    seed: int = 42,
) -> Tuple[nx.DiGraph, Dict[str, int]]:
    """Create a labeled payout graph with merchants, legitimate accounts, and mule rings."""
    rng = random.Random(seed)
    graph = nx.DiGraph()
    labels: Dict[str, int] = {}
    base_time = datetime(2026, 8, 1, 9, 0, 0)

    merchants = [f"MERCH_{i + 1:02d}" for i in range(n_merchants)]
    for merchant in merchants:
        graph.add_node(merchant, node_type="merchant", label="legitimate", account_id=merchant)
        labels[merchant] = 0

    cluster_accounts: List[str] = []
    for cluster_idx in range(n_clusters):
        size = rng.randint(cluster_size_range[0], cluster_size_range[1])
        for member_idx in range(size):
            account_id = f"ACC_MC_{cluster_idx + 1}_{member_idx + 1}"
            cluster_accounts.append(account_id)
            graph.add_node(
                account_id,
                node_type="beneficiary",
                label="mule",
                cluster_id=f"CLUSTER_{cluster_idx + 1}",
                account_id=account_id,
            )
            labels[account_id] = 1

    target_mules = max(1, int(n_beneficiaries * mule_ratio))
    individual_mules = max(0, target_mules - len(cluster_accounts))
    legitimate_count = max(0, n_beneficiaries - len(cluster_accounts) - individual_mules)

    legitimate_accounts = [f"ACC_L_{i + 1:03d}" for i in range(legitimate_count)]
    mule_accounts = [f"ACC_M_{i + 1:03d}" for i in range(individual_mules)]

    for account_id in legitimate_accounts:
        graph.add_node(account_id, node_type="beneficiary", label="legitimate", account_id=account_id)
        labels[account_id] = 0

    for account_id in mule_accounts:
        graph.add_node(account_id, node_type="beneficiary", label="mule", account_id=account_id)
        labels[account_id] = 1

    for account_id in legitimate_accounts:
        for idx in range(rng.randint(1, 4)):
            _add_edge(
                graph,
                rng.choice(merchants),
                account_id,
                amount=rng.uniform(1200, 52000),
                timestamp=base_time + timedelta(days=rng.randint(0, 21), hours=idx * 6),
                rng=rng,
            )

    mule_like_accounts = mule_accounts + cluster_accounts
    cashout_accounts = [f"CASHOUT_{i + 1:02d}" for i in range(max(6, len(mule_like_accounts) // 2))]
    for account_id in cashout_accounts:
        graph.add_node(account_id, node_type="beneficiary", label="cashout", account_id=account_id)
        labels[account_id] = 0

    for account_id in mule_accounts:
        incoming_total = 0.0
        for idx in range(rng.randint(4, 9)):
            amount = rng.uniform(45000, 260000)
            incoming_total += amount
            _add_edge(
                graph,
                rng.choice(merchants),
                account_id,
                amount=amount,
                timestamp=base_time + timedelta(hours=rng.randint(0, 36), minutes=idx * 11),
                rng=rng,
            )
        for idx in range(rng.randint(2, 5)):
            _add_edge(
                graph,
                account_id,
                rng.choice(cashout_accounts),
                amount=incoming_total * rng.uniform(0.12, 0.28),
                timestamp=base_time + timedelta(hours=rng.randint(6, 48), minutes=idx * 9),
                rng=rng,
            )

    clusters = {}
    for account_id in cluster_accounts:
        clusters.setdefault(graph.nodes[account_id]["cluster_id"], []).append(account_id)

    for members in clusters.values():
        for account_id in members:
            for idx in range(rng.randint(2, 5)):
                _add_edge(
                    graph,
                    rng.choice(merchants),
                    account_id,
                    amount=rng.uniform(35000, 180000),
                    timestamp=base_time + timedelta(hours=rng.randint(0, 24), minutes=idx * 7),
                    rng=rng,
                )
            peer_choices = [peer for peer in members if peer != account_id]
            if peer_choices:
                _add_edge(
                    graph,
                    account_id,
                    rng.choice(peer_choices),
                    amount=rng.uniform(18000, 90000),
                    timestamp=base_time + timedelta(hours=rng.randint(8, 48)),
                    rng=rng,
                )

    return graph, labels


def generate_held_out_test_set(
    n_beneficiaries: int = 50,
    mule_ratio: float = 0.15,
    seed: int = 99,
) -> Tuple[nx.DiGraph, Dict[str, int]]:
    """Generate a deterministic, unseen graph for evaluation."""
    return generate_razorpay_payout_graph(
        n_merchants=2,
        n_beneficiaries=n_beneficiaries,
        mule_ratio=mule_ratio,
        n_clusters=2,
        seed=seed,
    )


def generate_cold_start_accounts(n: int = 5, seed: int = 7) -> List[Dict]:
    """Create accounts with no transaction history and only weak device signals."""
    rng = random.Random(seed)
    return [
        {
            "account_id": f"ACC_COLD_{idx + 1:02d}",
            "out_degree": 0,
            "in_degree": 0,
            "total_sent": 0.0,
            "total_recv": 0.0,
            "device_id": f"DEV_{rng.randint(1000, 9999)}",
            "ip_address": f"192.168.{rng.randint(1, 255)}.{rng.randint(1, 255)}",
            "device_risk": round(rng.uniform(0.18, 0.62), 4),
            "created_at": datetime(2026, 8, 20, 10, idx, 0).isoformat(),
        }
        for idx in range(n)
    ]


def _add_edge(graph: nx.DiGraph, source: str, target: str, amount: float, timestamp: datetime, rng: random.Random) -> None:
    graph.add_edge(
        source,
        target,
        amount=round(amount, 2),
        timestamp=timestamp.isoformat() + "Z",
        status="processed",
        edge_type="sent_to",
        utr=f"UTR{rng.randint(100000000000, 999999999999)}",
    )
