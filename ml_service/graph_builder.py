"""
graph_builder.py — MuleNet Fraud Knowledge Graph Engine
Uses NetworkX instead of DGL (avoids distutils/Python3.13 conflict).
Implements the full multi-layer decisioning architecture:
  Layer 1: Data Ingestion → Graph Construction (Trust Data Fabric)
  Layer 2: Real-Time Risk Mesh (feature computation)
  Layer 3: Fraud Knowledge Graph (topology)
  Layer 5A: Fast Path — real XGBoost scoring
  Layer 5B: Deep Path — real Graph Neural Network scoring
  Layer 6: Risk Fusion & Decision Engine
  Layer 7: Policy Orchestration + Explainability
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
import networkx as nx
import math
import datetime
import time
import os

# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────

from pydantic.alias_generators import to_camel

class BaseModelCamel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

class Transaction(BaseModelCamel):
    utr: str
    amount: float
    timestamp: str
    sender_account: str
    receiver_account: str
    device_id: Optional[str] = None


class Complaint(BaseModelCamel):
    complaint_id: str
    utr: str
    amount: float
    timestamp: str
    first_beneficiary: str


class IntakeRequest(BaseModelCamel):
    complaint: Complaint
    transactions: List[Transaction]


# ─────────────────────────────────────────────────────────────────────────────
# Configurable fusion weights (Layer 6)
# ─────────────────────────────────────────────────────────────────────────────

FUSION_WEIGHTS = {
    "fast_path":  float(os.environ.get("FUSION_W_FAST", "0.30")),
    "gnn":        float(os.environ.get("FUSION_W_GNN", "0.35")),
    "topology":   float(os.environ.get("FUSION_W_TOPO", "0.20")),
    "external":   float(os.environ.get("FUSION_W_EXT", "0.15")),
}

MODEL_VERSION = "2.0.0"


# ─────────────────────────────────────────────────────────────────────────────
# I.  Trust Data Fabric — entity resolution + graph construction
# ─────────────────────────────────────────────────────────────────────────────

def build_hetero_graph(request: IntakeRequest) -> nx.DiGraph:
    """
    Construct a directed heterogeneous NetworkX graph from the intake request.
    Node types : account | device | complaint
    Edge types  : sent_to | uses_device | linked_to_case
    """
    G = nx.DiGraph()

    # Add complaint node
    G.add_node(
        f"complaint:{request.complaint.complaint_id}",
        node_type="complaint",
        amount=request.complaint.amount,
        utr=request.complaint.utr,
    )

    # Add account + device nodes, transaction edges
    for txn in request.transactions:
        for acct in [txn.sender_account, txn.receiver_account]:
            if not G.has_node(f"account:{acct}"):
                G.add_node(f"account:{acct}", node_type="account", total_sent=0.0, total_recv=0.0)

        G.nodes[f"account:{txn.sender_account}"]["total_sent"] += txn.amount
        G.nodes[f"account:{txn.receiver_account}"]["total_recv"] += txn.amount

        G.add_edge(
            f"account:{txn.sender_account}",
            f"account:{txn.receiver_account}",
            edge_type="sent_to",
            amount=txn.amount,
            utr=txn.utr,
            timestamp=txn.timestamp,
        )

        if txn.device_id:
            dev_node = f"device:{txn.device_id}"
            if not G.has_node(dev_node):
                G.add_node(dev_node, node_type="device")
            G.add_edge(f"account:{txn.sender_account}", dev_node, edge_type="uses_device")
            G.add_edge(f"account:{txn.receiver_account}", dev_node, edge_type="uses_device")

    # Link complaint to first beneficiary
    G.add_edge(
        f"complaint:{request.complaint.complaint_id}",
        f"account:{request.complaint.first_beneficiary}",
        edge_type="linked_to_case",
    )

    return G


# ─────────────────────────────────────────────────────────────────────────────
# II. Real-Time Risk Mesh — feature computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_features(G: nx.DiGraph, request: IntakeRequest) -> Dict[str, Dict]:
    features = {}
    account_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "account"]
    total_amount = sum(t.amount for t in request.transactions) or 1.0

    for node in account_nodes:
        acct_id = node.replace("account:", "")
        out_deg = G.out_degree(node)
        in_deg = G.in_degree(node)
        out_amounts = [G[node][nb]["amount"] for nb in G.successors(node)
                       if G[node][nb].get("edge_type") == "sent_to"]
        in_amounts = [G[nb][node]["amount"] for nb in G.predecessors(node)
                      if G[nb][node].get("edge_type") == "sent_to"]

        total_sent = sum(out_amounts) or 0.0
        total_recv = sum(in_amounts) or 0.0
        pass_through = min(total_sent, total_recv) / (max(total_sent, total_recv) + 1e-9)

        # Fan-out ratio
        fan_out = out_deg / (in_deg + 1)

        # Counterparty entropy (diversity of destinations)
        dest_amounts = out_amounts
        if dest_amounts:
            probs = [a / (total_sent + 1e-9) for a in dest_amounts]
            entropy = -sum(p * math.log(p + 1e-9) for p in probs)
        else:
            entropy = 0.0

        features[acct_id] = {
            "out_degree": out_deg,
            "in_degree": in_deg,
            "total_sent": total_sent,
            "total_recv": total_recv,
            "pass_through_rate": round(pass_through, 4),
            "fan_out_ratio": round(fan_out, 4),
            "counterparty_entropy": round(entropy, 4),
            "share_of_total_flow": round(total_sent / total_amount, 4),
        }

    return features


# ─────────────────────────────────────────────────────────────────────────────
# III. Graph Topology Scoring (centrality-based)
# ─────────────────────────────────────────────────────────────────────────────

def topology_scores(G: nx.DiGraph, features: Dict) -> Dict[str, float]:
    """Graph topology scoring — PageRank, ring detection, centrality."""
    scores = {}
    try:
        pagerank = nx.pagerank(G, weight=None, max_iter=100)
    except Exception:
        pagerank = {n: 0 for n in G.nodes()}

    try:
        betweenness = nx.betweenness_centrality(G)
    except Exception:
        betweenness = {n: 0 for n in G.nodes()}

    for acct, f in features.items():
        node_id = f"account:{acct}"
        pr = pagerank.get(node_id, 0) * 1000
        bw = betweenness.get(node_id, 0) * 100
        score = pr * 30 + bw * 20 + f["out_degree"] * 3
        scores[acct] = min(round(score, 2), 100.0)
    return scores


# ─────────────────────────────────────────────────────────────────────────────
# IV. Policy Orchestration + Explainability
# ─────────────────────────────────────────────────────────────────────────────

def _recommend_action(score: float) -> str:
    if score >= 80:
        return "FREEZE_IMMEDIATE"
    elif score >= 60:
        return "SOFT_HOLD"
    elif score >= 40:
        return "STEP_UP_MONITOR"
    elif score >= 20:
        return "MONITOR"
    else:
        return "ALLOW"


def build_explainability(
    acct: str, features: Dict, fast_score: float, gnn_score: float,
    topo_score: float, ext_uplift: float, composite: float
) -> Dict:
    f = features[acct]
    top_factors = []
    if f["pass_through_rate"] > 0.7:
        top_factors.append("high pass-through (mule behavior)")
    if f["out_degree"] > 3:
        top_factors.append("fan-out ring detected")
    if gnn_score > 0.6:
        top_factors.append("GNN: high-risk neighborhood embedding")
    if ext_uplift > 0:
        top_factors.append("external intelligence hit")
    if f["counterparty_entropy"] > 1.0:
        top_factors.append("high counterparty diversity")

    factors_str = "; ".join(top_factors) if top_factors else "moderate baseline risk"

    return {
        "technical": (
            f"Account {acct}: XGB={fast_score:.3f}, GNN={gnn_score:.3f}, "
            f"topo={topo_score:.1f}, ext_uplift={ext_uplift:.1f}, "
            f"pass_through={f['pass_through_rate']}, entropy={f['counterparty_entropy']}, "
            f"composite={composite:.1f}"
        ),
        "operational": f"Action: {_recommend_action(composite)} — {factors_str}.",
        "top_risk_factors": top_factors,
        "score_breakdown": {
            "fast_path_xgb": round(fast_score, 4),
            "gnn_score": round(gnn_score, 4),
            "topology_score": round(topo_score, 2),
            "external_uplift": round(ext_uplift, 2),
            "composite": round(composite, 2),
        },
        "regulator_ready": {
            "rule_flags": fast_score > 0.5,
            "graph_centrality_elevated": f["out_degree"] > 2,
            "pass_through_threshold_exceeded": f["pass_through_rate"] > 0.8,
            "external_watchlist_hit": ext_uplift > 0,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# V. Main inference entry point — REAL MODELS
# ─────────────────────────────────────────────────────────────────────────────

def real_inference(G: nx.DiGraph, request: IntakeRequest) -> Dict[str, Any]:
    """
    Full multi-layer decisioning pipeline with REAL ML models.
    No mocks — uses trained XGBoost and Graph Attention Network.
    """
    timings = {}
    t0 = time.time()

    # ── Layer 2: Feature computation ──
    t = time.time()
    features = compute_features(G, request)
    timings["feature_computation_ms"] = round((time.time() - t) * 1000, 2)

    if not features:
        return {
            "status": "ok",
            "model_version": MODEL_VERSION,
            "mule_probabilities": {},
            "recovery_ranking": [],
            "suspicious_edges": [],
            "explainability": {},
            "policy_actions": [],
            "graph_stats": {"nodes": G.number_of_nodes(), "edges": G.number_of_edges()},
            "timings": timings,
        }

    # ── Layer 3: Topology scoring ──
    t = time.time()
    topo = topology_scores(G, features)
    timings["topology_scoring_ms"] = round((time.time() - t) * 1000, 2)

    # ── Layer 5A: Fast Path — XGBoost ──
    t = time.time()
    from ml_models import get_fast_path
    fast_path = get_fast_path()
    fast_scores = fast_path.predict(features)
    timings["xgboost_inference_ms"] = round((time.time() - t) * 1000, 2)

    # ── Layer 5B: Deep Path — GNN ──
    t = time.time()
    from ml_models import get_gnn_scorer
    gnn = get_gnn_scorer()
    gnn_scores = gnn.predict(G, features)
    timings["gnn_inference_ms"] = round((time.time() - t) * 1000, 2)

    # ── External Intelligence (stub) ──
    t = time.time()
    from external_intel import batch_check
    device_map = {}
    for txn in request.transactions:
        if txn.device_id:
            device_map.setdefault(txn.sender_account, []).append(txn.device_id)
            device_map.setdefault(txn.receiver_account, []).append(txn.device_id)
    ext_results = batch_check(list(features.keys()), device_map)
    timings["external_intel_ms"] = round((time.time() - t) * 1000, 2)

    # ── Layer 6: Risk Fusion ──
    t = time.time()
    acct_ids = list(features.keys())
    ranking = []

    for acct in acct_ids:
        fast_prob = fast_scores.get(acct, 0)
        gnn_prob = gnn_scores.get(acct, 0)
        topo_score = topo.get(acct, 0)
        ext_uplift = ext_results[acct].risk_uplift if acct in ext_results else 0

        # Fusion: weighted combination, scaled to 0-100
        composite = (
            fast_prob * 100 * FUSION_WEIGHTS["fast_path"]
            + gnn_prob * 100 * FUSION_WEIGHTS["gnn"]
            + topo_score * FUSION_WEIGHTS["topology"]
            + ext_uplift * FUSION_WEIGHTS["external"]
        )
        composite = min(round(composite, 2), 100.0)

        confidence_band = "HIGH" if composite > 70 else "MEDIUM" if composite > 40 else "LOW"

        ranking.append({
            "account_id": acct,
            "composite_score": composite,
            "confidence_band": confidence_band,
            "fast_path_score": round(fast_prob, 4),
            "gnn_score": round(gnn_prob, 4),
            "topology_score": round(topo_score, 2),
            "external_uplift": round(ext_uplift, 2),
            "total_sent": features[acct]["total_sent"],
            "total_recv": features[acct].get("total_recv", 0),
            "pass_through_rate": features[acct]["pass_through_rate"],
            "out_degree": features[acct]["out_degree"],
            "action_recommendation": _recommend_action(composite),
        })

    ranking.sort(key=lambda x: x["composite_score"], reverse=True)
    timings["risk_fusion_ms"] = round((time.time() - t) * 1000, 2)

    # ── Recovery Intelligence (Layer 9) ──
    t = time.time()
    from recovery_engine import compute_freeze_ordering, compute_recovery_summary, trace_fund_paths

    mule_probs = {r["account_id"]: r["composite_score"] / 100.0 for r in ranking}

    freeze_ordering = compute_freeze_ordering(
        G, mule_probs, features, request.complaint.amount
    )
    recovery_summary = compute_recovery_summary(freeze_ordering, request.complaint.amount)
    fund_paths = trace_fund_paths(G, request.complaint.first_beneficiary if hasattr(request.complaint, 'first_beneficiary') else "AC-VICTIM")
    timings["recovery_engine_ms"] = round((time.time() - t) * 1000, 2)

    # ── Suspicious edges ──
    suspicious_edges = [
        {
            "from": u.replace("account:", ""),
            "to": v.replace("account:", ""),
            "amount": data.get("amount", 0),
            "utr": data.get("utr", ""),
            "timestamp": data.get("timestamp", ""),
        }
        for u, v, data in G.edges(data=True)
        if data.get("edge_type") == "sent_to"
    ]

    # ── Explainability (top 5) ──
    explainability = {}
    for r in ranking[:5]:
        acct = r["account_id"]
        ext_up = ext_results[acct].risk_uplift if acct in ext_results else 0
        explainability[acct] = build_explainability(
            acct, features,
            fast_scores.get(acct, 0),
            gnn_scores.get(acct, 0),
            topo.get(acct, 0),
            ext_up,
            r["composite_score"],
        )

    # ── External intelligence summary ──
    external_intel_summary = {}
    for acct, enrichment in ext_results.items():
        external_intel_summary[acct] = {
            "watchlist_hits": len(enrichment.watchlist_hits),
            "risk_uplift": enrichment.risk_uplift,
            "i4c_status": enrichment.i4c_status,
            "ncrp_complaints": enrichment.ncrp_complaints,
            "known_mule": enrichment.known_mule,
            "hit_details": [
                {"source": h.source, "match_type": h.match_type, "confidence": h.confidence}
                for h in enrichment.watchlist_hits
            ],
        }

    timings["total_pipeline_ms"] = round((time.time() - t0) * 1000, 2)

    return {
        "status": "ok",
        "model_version": MODEL_VERSION,
        "case_id": request.complaint.complaint_id,
        "analyzed_at": datetime.datetime.utcnow().isoformat() + "Z",
        "mule_probabilities": mule_probs,
        "recovery_ranking": ranking,
        "suspicious_edges": suspicious_edges,
        "explainability": explainability,
        "external_intelligence": external_intel_summary,
        "freeze_ordering": freeze_ordering,
        "recovery_summary": recovery_summary,
        "fund_paths": fund_paths,
        "policy_actions": [
            {"account_id": r["account_id"], "action": r["action_recommendation"],
             "confidence": r["confidence_band"], "composite_score": r["composite_score"]}
            for r in ranking if r["composite_score"] > 20
        ],
        "fusion_weights": FUSION_WEIGHTS,
        "graph_stats": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "account_nodes": len(features),
        },
        "timings": timings,
    }
