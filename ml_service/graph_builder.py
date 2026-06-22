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

from pydantic import BaseModel, ConfigDict, Field
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
    utr: str = Field(min_length=8)
    amount: float = Field(gt=0)
    timestamp: str
    sender_account: str = Field(min_length=3)
    receiver_account: str = Field(min_length=3)
    device_id: Optional[str] = Field(None, min_length=3)
    ip_address: Optional[str] = Field(None, min_length=7)


class Complaint(BaseModelCamel):
    complaint_id: str = Field(min_length=3)
    utr: str = Field(min_length=8)
    amount: float = Field(gt=0)
    timestamp: str
    first_beneficiary: str = Field(min_length=3)


class IntakeRequest(BaseModelCamel):
    complaint: Complaint
    transactions: List[Transaction] = Field(min_items=1)


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
# I.  Trust Data Fabric — Entity Resolution & Stateful Graph Store (Gaps 2, 3, 6)
# ─────────────────────────────────────────────────────────────────────────────

# Initialize Redis for Online Feature Store (Gap 3)
REDIS_CONN = None
try:
    import redis
    import os
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_CONN = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    REDIS_CONN.ping()
    print("[Redis] Online Feature Store connection active.")
except Exception:
    print("[Redis] Online Feature Store connection inactive, using local in-memory fallback.")

GLOBAL_GRAPH = nx.DiGraph()
GLOBAL_TXNS = []
COMPLAINT_RISK_UPLIFTS = {}

MERCHANTS = {"AC-MERCHANT", "AC-ECOM", "AC-PG-GATEWAY"}

def parse_time(ts_str):
    try:
        s = ts_str.replace('Z', '')
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return datetime.datetime.utcnow()

def build_hetero_graph(request: IntakeRequest) -> nx.DiGraph:
    """
    Construct a stateful, directed heterogeneous NetworkX graph (Gap 2).
    Nodes and edges are persisted globally.
    """
    global GLOBAL_GRAPH, GLOBAL_TXNS, COMPLAINT_RISK_UPLIFTS
    
    # 1. Store transactions in Online Feature Store cache
    if request.transactions:
        GLOBAL_TXNS.extend(request.transactions)
        
    # Sync ingestion data to Neo4j database if active
    from neo4j_store import get_neo4j_graph
    neo4j_graph = get_neo4j_graph()
    if neo4j_graph.enabled:
        try:
            neo4j_graph.add_complaint(
                request.complaint.complaint_id,
                request.complaint.amount,
                request.complaint.utr,
                request.complaint.timestamp,
                request.complaint.first_beneficiary
            )
            for txn in request.transactions:
                neo4j_graph.add_transaction(
                    txn.sender_account,
                    txn.receiver_account,
                    txn.amount,
                    txn.timestamp,
                    txn.utr,
                    txn.sender_account in MERCHANTS,
                    txn.receiver_account in MERCHANTS
                )
                if txn.device_id:
                    neo4j_graph.add_device_link(txn.sender_account, txn.device_id)
                    neo4j_graph.add_device_link(txn.receiver_account, txn.device_id)
        except Exception as e:
            print(f"[Neo4j] Live data replication failed: {e}")
        
    # 2. Add nodes and edges to live graph
    comp_id = f"complaint:{request.complaint.complaint_id}"
    GLOBAL_GRAPH.add_node(
        comp_id,
        node_type="complaint",
        amount=request.complaint.amount,
        utr=request.complaint.utr,
        timestamp=request.complaint.timestamp
    )
    
    for txn in request.transactions:
        for acct in [txn.sender_account, txn.receiver_account]:
            acct_node = f"account:{acct}"
            is_merchant = acct in MERCHANTS
            if not GLOBAL_GRAPH.has_node(acct_node):
                GLOBAL_GRAPH.add_node(
                    acct_node, 
                    node_type="merchant" if is_merchant else "account", 
                    total_sent=0.0, 
                    total_recv=0.0
                )
            elif is_merchant:
                GLOBAL_GRAPH.nodes[acct_node]["node_type"] = "merchant"

        GLOBAL_GRAPH.nodes[f"account:{txn.sender_account}"]["total_sent"] += txn.amount
        GLOBAL_GRAPH.nodes[f"account:{txn.receiver_account}"]["total_recv"] += txn.amount

        GLOBAL_GRAPH.add_edge(
            f"account:{txn.sender_account}",
            f"account:{txn.receiver_account}",
            edge_type="sent_to",
            amount=txn.amount,
            utr=txn.utr,
            timestamp=txn.timestamp,
        )

        if txn.device_id:
            dev_node = f"device:{txn.device_id}"
            if not GLOBAL_GRAPH.has_node(dev_node):
                GLOBAL_GRAPH.add_node(dev_node, node_type="device")
            GLOBAL_GRAPH.add_edge(f"account:{txn.sender_account}", dev_node, edge_type="uses_device")
            GLOBAL_GRAPH.add_edge(f"account:{txn.receiver_account}", dev_node, edge_type="uses_device")

    # Link complaint to first beneficiary
    beneficiary_node = f"account:{request.complaint.first_beneficiary}"
    GLOBAL_GRAPH.add_edge(comp_id, beneficiary_node, edge_type="linked_to_case")

    # 3. Complaint Propagation Engine BFS (Gap 6)
    # Start BFS at first beneficiary, propagate risk down 3 hops
    visited = set()
    queue = [(beneficiary_node, 30.0)]  # node, initial risk propagation score
    
    while queue:
        node, score = queue.pop(0)
        if node in visited or score < 5.0:
            continue
        visited.add(node)
        
        acct_id = node.replace("account:", "")
        if acct_id not in COMPLAINT_RISK_UPLIFTS:
            COMPLAINT_RISK_UPLIFTS[acct_id] = 0.0
        COMPLAINT_RISK_UPLIFTS[acct_id] = max(COMPLAINT_RISK_UPLIFTS[acct_id], score)
        
        # Traverse neighbors (counter-parties or shared devices)
        for neighbor in GLOBAL_GRAPH.successors(node):
            if neighbor.startswith("account:") or neighbor.startswith("device:"):
                decay = 0.7 if neighbor.startswith("device:") else 0.5
                queue.append((neighbor, score * decay))
        for neighbor in GLOBAL_GRAPH.predecessors(node):
            if neighbor.startswith("account:") or neighbor.startswith("device:"):
                decay = 0.7 if neighbor.startswith("device:") else 0.5
                queue.append((neighbor, score * decay))

    return GLOBAL_GRAPH


# ─────────────────────────────────────────────────────────────────────────────
# II. Real-Time Risk Mesh — Feature Computation & Online Feature Store (Gap 3)
# ─────────────────────────────────────────────────────────────────────────────

def compute_features(G: nx.DiGraph, request: IntakeRequest) -> Dict[str, Dict]:
    global GLOBAL_TXNS, COMPLAINT_RISK_UPLIFTS
    features = {}
    account_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") in ["account", "merchant"]]
    total_amount = sum(t.amount for t in request.transactions) or 1.0
    query_time = parse_time(request.complaint.timestamp)

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
        fan_out = out_deg / (in_deg + 1)

        dest_amounts = out_amounts
        if dest_amounts:
            probs = [a / (total_sent + 1e-9) for a in dest_amounts]
            entropy = -sum(p * math.log(p + 1e-9) for p in probs)
        else:
            entropy = 0.0

        # ── Online Feature Store (Gap 3) — Sliding Windows ──
        sender_5m = 0
        recv_30m_funds = 0.0
        sent_60m_funds = 0.0
        recv_60m_funds = 0.0
        cash_out_velocity = 0.0
        redis_success = False

        if REDIS_CONN:
            try:
                cached = REDIS_CONN.hgetall(f"features:{acct_id}")
                if cached:
                    sender_5m = int(cached.get("sender_5min_count", 0))
                    recv_30m_funds = float(cached.get("receiver_30min_inflow", 0.0))
                    cash_out_velocity = float(cached.get("cash_out_velocity", 0.0))
                    redis_success = True
            except Exception as e:
                pass

        if not redis_success:
            for txn in GLOBAL_TXNS:
                txn_time = parse_time(txn.timestamp)
                delta = (query_time - txn_time).total_seconds()
                
                # 5-minute sliding window for sender count
                if txn.sender_account == acct_id and 0 <= delta <= 300:
                    sender_5m += 1
                    
                # 30-minute sliding window for receiver inflow
                if txn.receiver_account == acct_id and 0 <= delta <= 1800:
                    recv_30m_funds += txn.amount
                    
                # 60-minute sliding window for velocity
                if 0 <= delta <= 3600:
                    if txn.sender_account == acct_id:
                        sent_60m_funds += txn.amount
                    if txn.receiver_account == acct_id:
                        recv_60m_funds += txn.amount
                        
            cash_out_velocity = sent_60m_funds / (recv_60m_funds + 1e-9)


        # Proximity to complaint nodes
        complaint_prox = 99
        complaint_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "complaint"]
        for c_node in complaint_nodes:
            try:
                dist = nx.shortest_path_length(G, source=c_node, target=node)
                if dist < complaint_prox:
                    complaint_prox = dist
            except Exception:
                pass

        complaint_uplift = COMPLAINT_RISK_UPLIFTS.get(acct_id, 0.0)

        features[acct_id] = {
            "out_degree": out_deg,
            "in_degree": in_deg,
            "total_sent": total_sent,
            "total_recv": total_recv,
            "pass_through_rate": round(pass_through, 4),
            "fan_out_ratio": round(fan_out, 4),
            "counterparty_entropy": round(entropy, 4),
            "share_of_total_flow": round(total_sent / total_amount, 4),
            
            # Sliding window online store metrics
            "sender_5min_count": sender_5m,
            "receiver_30min_inflow": round(recv_30m_funds, 2),
            "cash_out_velocity": round(cash_out_velocity, 4),
            "complaint_proximity": complaint_prox,
            "complaint_uplift": round(complaint_uplift, 2),
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
    
    # ── Dynamic Compliance Narrative Generator (Gap 12) ──
    in_amount = f.get("total_recv", 0.0)
    out_amount = f.get("total_sent", 0.0)
    pt_rate = f.get("pass_through_rate", 0.0)
    out_deg = f.get("out_degree", 0)
    prox = f.get("complaint_proximity", 99)
    entropy = f.get("counterparty_entropy", 0.0)
    action = _recommend_action(composite)
    is_merchant = acct in MERCHANTS

    narrative = f"Entity '{acct}' has been flagged under compliance review. "
    if is_merchant:
        narrative += f"The account is a registered merchant, but displays atypical high-volume pattern spikes. "
    else:
        narrative += f"The account received a total inflow of ₹{in_amount:,.2f} and rapidly routed ₹{out_amount:,.2f} out. "
    
    narrative += f"The pass-through velocity rate was calculated at {pt_rate * 100:.1f}%, with a fan-out layering chain involving {out_deg} counterparties. "
    
    if ext_uplift > 0:
        narrative += f"External registries (I4C/NCRP) returned positive matches (+{ext_uplift} uplift). "
        
    if prox <= 2:
        narrative += f"Graph path analysis identified immediate proximity ({prox} hops) to complainant node clusters. "
        
    if entropy > 1.0:
        narrative += f"Counterparty diversity entropy ({entropy:.2f}) indicates an active layering transaction ring. "
        
    narrative += f"Compliance Recommendation: Execute {action.replace('_', ' ')} protocol immediately."

    return {
        "technical": (
            f"Account {acct}: XGB={fast_score:.3f}, GNN={gnn_score:.3f}, "
            f"topo={topo_score:.1f}, ext_uplift={ext_uplift:.1f}, "
            f"pass_through={f['pass_through_rate']}, entropy={f['counterparty_entropy']}, "
            f"composite={composite:.1f}"
        ),
        "operational": f"Action: {action} — {factors_str}.",
        "compliance_narrative": narrative,
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
    No mocks — uses trained XGBoost, Graph Attention Network, and Isolation Forest.
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

    # ── Layer 5C: Unsupervised Anomaly Path — Isolation Forest (Gap 7) ──
    t = time.time()
    from ml_models import get_anomaly_detector
    ad = get_anomaly_detector()
    anomaly_scores = ad.predict(features)
    timings["isolation_forest_ms"] = round((time.time() - t) * 1000, 2)

    # ── External Intelligence ──
    t = time.time()
    from external_intel import batch_check
    device_map = {}
    ip_map = {}
    for txn in request.transactions:
        if txn.device_id:
            device_map.setdefault(txn.sender_account, []).append(txn.device_id)
            device_map.setdefault(txn.receiver_account, []).append(txn.device_id)
        if txn.ip_address:
            ip_map.setdefault(txn.sender_account, []).append(txn.ip_address)
            ip_map.setdefault(txn.receiver_account, []).append(txn.ip_address)
    ext_results = batch_check(list(features.keys()), device_map, ip_map)
    timings["external_intel_ms"] = round((time.time() - t) * 1000, 2)

    # ── Layer 6: Risk Fusion & Platt Sigmoid Calibration (Gap 9) ──
    t = time.time()
    acct_ids = list(features.keys())
    ranking = []
    from ml_models import calibrate_score

    for acct in acct_ids:
        fast_prob = fast_scores.get(acct, 0)
        gnn_prob = gnn_scores.get(acct, 0)
        topo_score = topo.get(acct, 0)
        ext_uplift = ext_results[acct].risk_uplift if acct in ext_results else 0
        anomaly_score = anomaly_scores.get(acct, 0.0)
        complaint_uplift = features[acct].get("complaint_uplift", 0.0)

        # Base composite ensemble scoring
        raw_composite = (
            fast_prob * 100 * FUSION_WEIGHTS["fast_path"] * 0.85
            + gnn_prob * 100 * FUSION_WEIGHTS["gnn"]
            + topo_score * FUSION_WEIGHTS["topology"] * 0.8
            + anomaly_score * 100 * 0.15          # Unsupervised contribution
            + ext_uplift * FUSION_WEIGHTS["external"]
            + complaint_uplift                    # Propagated risk score addition
        )

        # Merchant Protection Layer (Gap 8)
        is_merchant = acct in MERCHANTS
        if is_merchant:
            # If high-volume profile matches normal merchant behavior (e.g. low pass-through rate), discount risk
            pt_rate = features[acct].get("pass_through_rate", 0.0)
            merchant_safety_factor = max(1.0 - pt_rate, 0.2)
            raw_composite = raw_composite * (1.0 - 0.75 * merchant_safety_factor)

        # Calibrate composite risk score using Platt Sigmoidal scaling
        composite = calibrate_score(raw_composite)

        confidence_band = "HIGH" if composite > 70 else "MEDIUM" if composite > 40 else "LOW"

        ranking.append({
            "account_id": acct,
            "composite_score": composite,
            "confidence_band": confidence_band,
            "fast_path_score": round(fast_prob, 4),
            "gnn_score": round(gnn_prob, 4),
            "topology_score": round(topo_score, 2),
            "anomaly_score": round(anomaly_score, 4),
            "external_uplift": round(ext_uplift, 2),
            "complaint_uplift": round(complaint_uplift, 2),
            "total_sent": features[acct]["total_sent"],
            "total_recv": features[acct].get("total_recv", 0),
            "pass_through_rate": features[acct]["pass_through_rate"],
            "out_degree": features[acct]["out_degree"],
            "in_degree": features[acct]["in_degree"],
            "fan_out_ratio": features[acct]["fan_out_ratio"],
            "counterparty_entropy": features[acct]["counterparty_entropy"],
            "share_of_total_flow": features[acct]["share_of_total_flow"],
            "is_merchant": is_merchant,
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
    suspicious_edges = []
    for u, v, data in G.edges(data=True):
        u_clean = u.replace("account:", "").replace("device:", "").replace("complaint:", "")
        v_clean = v.replace("account:", "").replace("device:", "").replace("complaint:", "")
        if data.get("edge_type") == "sent_to":
            suspicious_edges.append({
                "from": u_clean,
                "to": v_clean,
                "edge_type": "sent_to",
                "amount": data.get("amount", 0),
                "utr": data.get("utr", ""),
                "timestamp": data.get("timestamp", ""),
            })
        elif data.get("edge_type") == "uses_device":
            suspicious_edges.append({
                "from": u_clean,
                "to": v_clean,
                "edge_type": "uses_device"
            })
        elif data.get("edge_type") == "linked_to_case":
            suspicious_edges.append({
                "from": u_clean,
                "to": v_clean,
                "edge_type": "linked_to_case"
            })

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
