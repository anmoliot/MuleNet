"""
recovery_engine.py — Layer 9: Recovery Intelligence Engine
Multi-hop fund tracing, optimal freeze ordering, and fund recovery analysis.
"""

import networkx as nx
from typing import Dict, List, Any, Tuple
import math


def trace_fund_paths(
    G: nx.DiGraph,
    victim_account: str,
    max_depth: int = 6,
) -> List[Dict[str, Any]]:
    """
    Trace all fund paths from the victim account through the transaction graph.
    Returns ordered paths with amounts, depths, and time windows.
    """
    victim_node = f"account:{victim_account}"
    if victim_node not in G:
        return []

    paths = []
    visited = set()

    def dfs(node, current_path, current_amount, depth):
        if depth > max_depth:
            return
        visited.add(node)

        successors = [
            (nb, G[node][nb])
            for nb in G.successors(node)
            if G[node][nb].get("edge_type") == "sent_to" and nb not in visited
        ]

        if not successors and len(current_path) > 1:
            # Terminal node — record path
            paths.append({
                "path": [n.replace("account:", "") for n in current_path],
                "hops": len(current_path) - 1,
                "terminal_account": current_path[-1].replace("account:", ""),
                "traced_amount": current_amount,
                "is_endpoint": True,
            })
            return

        for successor, edge_data in successors:
            amount = edge_data.get("amount", 0)
            new_path = current_path + [successor]
            dfs(successor, new_path, amount, depth + 1)

        # Also record this node if it's a branching point
        if len(current_path) > 1 and len(successors) > 1:
            paths.append({
                "path": [n.replace("account:", "") for n in current_path],
                "hops": len(current_path) - 1,
                "terminal_account": current_path[-1].replace("account:", ""),
                "traced_amount": current_amount,
                "is_endpoint": False,
                "fan_out": len(successors),
            })

        visited.discard(node)

    dfs(victim_node, [victim_node], 0, 0)
    return sorted(paths, key=lambda p: p["hops"])


def compute_freeze_ordering(
    G: nx.DiGraph,
    mule_probabilities: Dict[str, float],
    features: Dict[str, Dict],
    complaint_amount: float,
) -> List[Dict[str, Any]]:
    """
    Determine optimal freeze ordering to maximize fund recovery.
    Accounts holding more funds and with higher mule probability should be frozen first.
    Incorporates time-decay: funds at rest longer are harder to recover.
    """
    candidates = []

    for acct, prob in mule_probabilities.items():
        if prob < 0.15:
            continue

        f = features.get(acct, {})
        total_recv = f.get("total_recv", 0)
        total_sent = f.get("total_sent", 0)
        balance_estimate = total_recv - total_sent  # Residual funds

        # Recovery potential = estimated balance × mule probability
        recovery_potential = max(balance_estimate, 0) * prob

        # Pass-through accounts (high sent/recv ratio) likely already moved funds
        pass_through = f.get("pass_through_rate", 0)
        retention_factor = 1.0 - (pass_through * 0.7)

        # Adjusted recovery score
        recovery_score = recovery_potential * retention_factor

        # Urgency: high fan-out = funds dispersing rapidly
        fan_out = f.get("fan_out_ratio", 0)
        urgency = "IMMEDIATE" if fan_out > 2 or prob > 0.7 else \
                  "HIGH" if prob > 0.5 else \
                  "MEDIUM" if prob > 0.3 else "LOW"

        candidates.append({
            "account_id": acct,
            "mule_probability": round(prob, 4),
            "estimated_balance": round(max(balance_estimate, 0), 2),
            "recovery_potential": round(recovery_score, 2),
            "retention_factor": round(retention_factor, 4),
            "urgency": urgency,
            "freeze_priority": 0,  # Will be set after sorting
            "recovery_pct_of_total": round(
                (recovery_score / complaint_amount) * 100, 2
            ) if complaint_amount > 0 else 0,
        })

    # Sort by recovery potential (highest first)
    candidates.sort(key=lambda c: c["recovery_potential"], reverse=True)

    # Assign priority ranks
    for i, c in enumerate(candidates):
        c["freeze_priority"] = i + 1

    return candidates


def compute_recovery_summary(
    freeze_ordering: List[Dict],
    complaint_amount: float,
) -> Dict[str, Any]:
    """
    Compute aggregate recovery intelligence metrics.
    """
    total_recoverable = sum(c["recovery_potential"] for c in freeze_ordering)
    immediate_targets = [c for c in freeze_ordering if c["urgency"] == "IMMEDIATE"]

    return {
        "complaint_amount": complaint_amount,
        "total_recoverable_estimate": round(total_recoverable, 2),
        "recovery_rate_pct": round(
            (total_recoverable / complaint_amount) * 100, 2
        ) if complaint_amount > 0 else 0,
        "accounts_to_freeze": len(freeze_ordering),
        "immediate_targets": len(immediate_targets),
        "top_recovery_target": freeze_ordering[0]["account_id"] if freeze_ordering else None,
    }
