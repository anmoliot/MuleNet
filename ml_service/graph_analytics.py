"""
graph_analytics.py — MuleNet Advanced Graph Analytics Engine

Provides:
  - Community detection (Label Propagation — no external dependency)
  - Fraud ring / cycle detection
  - Hub and coordinator node identification
  - Shortest fraud path discovery
  - Layering operation detection
  - Smurfing pattern detection
  - Centrality metrics (PageRank, Betweenness, Degree)
  - Connected fraud component enumeration
"""

import math
import networkx as nx
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════════
# COMMUNITY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_communities_label_propagation(
    G: nx.DiGraph,
    max_iterations: int = 20,
    seed: int = 42,
) -> Dict[str, int]:
    """
    Label Propagation Community Detection on a directed graph.
    Works by iteratively assigning each node the most common community label
    among its neighbors.

    Returns
    -------
    {node_id: community_id} mapping
    """
    G_undirected = G.to_undirected()

    account_nodes = [n for n, d in G.nodes(data=True)
                     if d.get("node_type") in ("account", "merchant", None)
                     and n.startswith("account:")]

    if not account_nodes:
        return {}

    import random
    rng = random.Random(seed)
    community = {n: i for i, n in enumerate(account_nodes)}
    node_set = set(account_nodes)

    for _ in range(max_iterations):
        changed = False
        nodes_shuffled = list(account_nodes)
        rng.shuffle(nodes_shuffled)

        for node in nodes_shuffled:
            neighbors = [nb for nb in G_undirected.neighbors(node) if nb in node_set]
            if not neighbors:
                continue

            freq: Dict[int, int] = defaultdict(int)
            for nb in neighbors:
                freq[community[nb]] += 1

            max_count = max(freq.values())
            candidates = [c for c, cnt in freq.items() if cnt == max_count]
            best = rng.choice(candidates)

            if community[node] != best:
                community[node] = best
                changed = True

        if not changed:
            break

    # Re-number communities 0..N-1
    unique_labels = sorted(set(community.values()))
    label_map = {old: new for new, old in enumerate(unique_labels)}
    return {n: label_map[c] for n, c in community.items()}


def get_community_statistics(
    G: nx.DiGraph,
    community_map: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Compute per-community statistics for fraud cluster analysis."""
    communities: Dict[int, List[str]] = defaultdict(list)
    for node, cid in community_map.items():
        communities[cid].append(node)

    stats = []
    for cid, members in communities.items():
        member_set = set(members)
        internal_edges = sum(
            1 for u, v in G.edges()
            if u in member_set and v in member_set
        )
        internal_flow = sum(
            d.get("amount", 0)
            for u, v, d in G.edges(data=True)
            if u in member_set and v in member_set
        )
        cross_edges = sum(
            1 for u, v in G.edges()
            if (u in member_set) != (v in member_set)
        )

        stats.append({
            "community_id": cid,
            "size": len(members),
            "members": [m.replace("account:", "") for m in members],
            "internal_edges": internal_edges,
            "cross_community_edges": cross_edges,
            "internal_flow": round(internal_flow, 2),
            "cohesion": round(internal_edges / max(len(members) * (len(members) - 1), 1), 4),
        })

    return sorted(stats, key=lambda x: x["size"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FRAUD RING DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_fraud_rings(
    G: nx.DiGraph,
    min_cycle_length: int = 2,
    max_cycle_length: int = 6,
) -> List[Dict[str, Any]]:
    """
    Detect transaction cycles (fraud rings / layering loops).

    A fraud ring is a directed cycle where funds flow through a closed loop
    of accounts — a strong indicator of layering activity.
    """
    acct_subgraph = nx.DiGraph([
        (u, v, d) for u, v, d in G.edges(data=True)
        if d.get("edge_type") == "sent_to"
        and u.startswith("account:") and v.startswith("account:")
    ])

    rings = []
    seen_cycles: Set[frozenset] = set()

    try:
        for cycle in nx.simple_cycles(acct_subgraph):
            if min_cycle_length <= len(cycle) <= max_cycle_length:
                cycle_key = frozenset(cycle)
                if cycle_key in seen_cycles:
                    continue
                seen_cycles.add(cycle_key)

                cycle_flow = 0.0
                for i, node in enumerate(cycle):
                    next_node = cycle[(i + 1) % len(cycle)]
                    if acct_subgraph.has_edge(node, next_node):
                        cycle_flow += acct_subgraph[node][next_node].get("amount", 0)

                rings.append({
                    "ring_id": f"RING-{len(rings) + 1:03d}",
                    "length": len(cycle),
                    "members": [n.replace("account:", "") for n in cycle],
                    "cycle_flow": round(cycle_flow, 2),
                    "risk_category": "LAYERING_RING" if len(cycle) >= 4 else "CIRCULAR_TRANSFER",
                })
    except Exception as e:
        print(f"[GraphAnalytics] Cycle detection error: {e}")

    return sorted(rings, key=lambda r: r["cycle_flow"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HUB AND COORDINATOR DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def identify_hub_accounts(
    G: nx.DiGraph,
    pagerank: Optional[Dict[str, float]] = None,
    betweenness: Optional[Dict[str, float]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Identify hub accounts (high-centrality money laundering coordinators).
    Hub accounts act as central nodes through which most funds flow.
    """
    if pagerank is None:
        try:
            pagerank = nx.pagerank(G, weight=None, max_iter=200)
        except Exception:
            pagerank = {n: 0.0 for n in G.nodes()}

    if betweenness is None:
        try:
            betweenness = nx.betweenness_centrality(G)
        except Exception:
            betweenness = {n: 0.0 for n in G.nodes()}

    account_nodes = [
        n for n, d in G.nodes(data=True)
        if d.get("node_type") in ("account", None)
        and n.startswith("account:")
    ]

    hubs = []
    for node in account_nodes:
        pr = pagerank.get(node, 0.0)
        bw = betweenness.get(node, 0.0)
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)
        hub_score = pr * 500 + bw * 200 + (in_deg + out_deg) * 2

        hubs.append({
            "account_id": node.replace("account:", ""),
            "pagerank": round(pr, 6),
            "betweenness_centrality": round(bw, 6),
            "in_degree": in_deg,
            "out_degree": out_deg,
            "hub_score": round(hub_score, 4),
            "role": "HUB" if bw > 0.3 else "COORDINATOR" if pr > 0.1 else "STANDARD",
        })

    return sorted(hubs, key=lambda x: x["hub_score"], reverse=True)[:top_n]


# ═══════════════════════════════════════════════════════════════════════════════
# SMURFING PATTERN DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_smurfing(
    G: nx.DiGraph,
    threshold_amount: float = 200000.0,
    min_accounts: int = 3,
) -> List[Dict[str, Any]]:
    """
    Detect smurfing patterns: a single account distributing funds to many
    smaller recipient accounts to avoid reporting thresholds.
    """
    smurf_suspects = []

    for node in G.nodes():
        if not node.startswith("account:"):
            continue

        successors = [
            (nb, G[node][nb])
            for nb in G.successors(node)
            if G[node][nb].get("edge_type") == "sent_to"
        ]

        if len(successors) < min_accounts:
            continue

        amounts = [d.get("amount", 0) for _, d in successors]
        total = sum(amounts)
        max_single = max(amounts) if amounts else 0
        avg_single = total / len(amounts) if amounts else 0

        # Classic smurfing: total is high but individual transfers are small
        if total >= threshold_amount and max_single < threshold_amount * 0.6:
            smurf_suspects.append({
                "account_id": node.replace("account:", ""),
                "recipient_count": len(successors),
                "total_distributed": round(total, 2),
                "max_single_transfer": round(max_single, 2),
                "avg_transfer": round(avg_single, 2),
                "recipients": [nb.replace("account:", "") for nb, _ in successors],
                "smurfing_score": round(
                    min(100, (len(successors) * 10) + (total / threshold_amount * 20)), 2
                ),
                "pattern": "SMURFING_DISTRIBUTION",
            })

    return sorted(smurf_suspects, key=lambda x: x["smurfing_score"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTED FRAUD COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

def find_connected_fraud_components(
    G: nx.DiGraph,
    high_risk_accounts: List[str],
) -> List[Dict[str, Any]]:
    """
    Find all weakly connected components that contain at least one high-risk
    account.
    """
    high_risk_nodes = {f"account:{a}" for a in high_risk_accounts}
    components = []

    for component in nx.weakly_connected_components(G):
        fraud_nodes_in_component = component & high_risk_nodes
        if not fraud_nodes_in_component:
            continue

        acct_nodes = {n for n in component if n.startswith("account:")}
        subgraph = G.subgraph(component)

        total_flow = sum(
            d.get("amount", 0)
            for _, _, d in subgraph.edges(data=True)
            if d.get("edge_type") == "sent_to"
        )

        components.append({
            "component_size": len(acct_nodes),
            "total_nodes": len(component),
            "high_risk_nodes": [n.replace("account:", "") for n in fraud_nodes_in_component],
            "all_accounts": [n.replace("account:", "") for n in acct_nodes],
            "total_flow": round(total_flow, 2),
            "edge_count": subgraph.number_of_edges(),
            "fraud_density": round(
                len(fraud_nodes_in_component) / max(len(acct_nodes), 1), 4
            ),
        })

    return sorted(components, key=lambda x: x["fraud_density"], reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SHORTEST FRAUD PATH
# ═══════════════════════════════════════════════════════════════════════════════

def find_shortest_fraud_paths(
    G: nx.DiGraph,
    source_account: str,
    target_accounts: List[str],
    max_paths: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find the shortest transaction paths from a source account to a set of
    target (high-risk) accounts. Used for fraud path tracing.
    """
    source_node = f"account:{source_account}"
    paths = []

    for target in target_accounts[:max_paths]:
        target_node = f"account:{target}"
        try:
            path = nx.shortest_path(G, source=source_node, target=target_node)
            path_value = 0.0
            for i in range(len(path) - 1):
                edge_data = G.get_edge_data(path[i], path[i + 1], default={})
                path_value += edge_data.get("amount", 0)

            paths.append({
                "source": source_account,
                "target": target,
                "hops": len(path) - 1,
                "path": [
                    n.replace("account:", "").replace("device:", "[DEV]")
                     .replace("complaint:", "[CASE]")
                    for n in path
                ],
                "path_value": round(path_value, 2),
            })
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

    return sorted(paths, key=lambda x: x["hops"])


# ═══════════════════════════════════════════════════════════════════════════════
# FULL GRAPH ANALYTICS REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def run_full_graph_analytics(
    G: nx.DiGraph,
    high_risk_accounts: Optional[List[str]] = None,
    victim_account: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the complete suite of graph analytics and return a consolidated report.
    """
    high_risk_accounts = high_risk_accounts or []

    community_map = detect_communities_label_propagation(G)
    community_stats = get_community_statistics(G, community_map)
    fraud_rings = detect_fraud_rings(G)
    hub_accounts = identify_hub_accounts(G)
    smurfing_patterns = detect_smurfing(G)
    fraud_components = find_connected_fraud_components(G, high_risk_accounts)

    shortest_paths = []
    if victim_account and high_risk_accounts:
        shortest_paths = find_shortest_fraud_paths(
            G, victim_account, high_risk_accounts[:5]
        )

    try:
        pagerank = nx.pagerank(G, weight=None, max_iter=200)
    except Exception:
        pagerank = {n: 0.0 for n in G.nodes()}

    node_community_info = {}
    for node, cid in community_map.items():
        acct_id = node.replace("account:", "")
        node_community_info[acct_id] = {
            "community_id": cid,
            "pagerank": round(pagerank.get(node, 0.0), 6),
        }

    return {
        "community_detection": {
            "algorithm": "LabelPropagation",
            "num_communities": len(set(community_map.values())),
            "node_communities": {
                n.replace("account:", ""): cid
                for n, cid in community_map.items()
            },
            "community_stats": community_stats[:10],
        },
        "fraud_rings": fraud_rings[:20],
        "hub_accounts": hub_accounts,
        "smurfing_patterns": smurfing_patterns[:10],
        "fraud_components": fraud_components[:10],
        "shortest_fraud_paths": shortest_paths,
        "node_analytics": node_community_info,
        "graph_summary": {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "account_nodes": sum(1 for n in G.nodes() if n.startswith("account:")),
            "fraud_rings_detected": len(fraud_rings),
            "communities_found": len(set(community_map.values())),
            "smurfing_suspects": len(smurfing_patterns),
        },
    }
