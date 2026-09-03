"""
main.py — MuleNet ML Service
Graph-Native Fraud Decisioning Platform — FastAPI entry point
Full 11-layer architecture with real ML models.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from graph_builder import build_hetero_graph, real_inference, IntakeRequest, MODEL_VERSION, FUSION_WEIGHTS
import networkx as nx
import asyncio
import json

from agent_loop import MuleNetDetectionAgent, compute_demo_features
from config import DEFAULT_MULE_RATIO, DEFAULT_SEED, DEFAULT_TEST_ACCOUNTS, DEFAULT_THRESHOLD, ALLOWED_ORIGINS
from metrics_evaluator import evaluate_on_held_out, threshold_sweep
from razorpay_simulator import (
    generate_cold_start_accounts,
    generate_razorpay_payout_graph,
)

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(
    title="MuleNet ML Engine",
    description="Graph-Native Fraud Decisioning — Real XGBoost + GNN Pipeline",
    version=MODEL_VERSION,
)

security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Placeholder JWT verification - replace with real public key / JWKS validation
    token = credentials.credentials
    # For demo purposes, accept any non-empty token
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIT_RUNS = {}


@app.get("/")
def health_check():
    return {"status": "ok", "service": "MuleNet ML Engine", "version": MODEL_VERSION}


@app.get("/api/health")
def detailed_health():
    """Detailed health check with model status."""
    from ml_models import get_model_metadata
    return {
        "status": "ok",
        "version": MODEL_VERSION,
        "models": get_model_metadata(),
        "fusion_weights": FUSION_WEIGHTS,
    }


@app.post("/api/analyze")
def analyze_graph(request: IntakeRequest):
    """
    Full multi-layer decisioning pipeline with REAL ML models:
    1. Trust Data Fabric  — entity resolution + graph construction
    2. Real-Time Risk Mesh — feature computation
    3. Fraud Knowledge Graph — topology scoring
    5A. Fast Path — trained XGBoost classifier
    5B. Deep Path — trained Graph Attention Network
    6. Risk Fusion — weighted ensemble scoring
    7. Policy Orchestration — action recommendations
    9. Recovery Intelligence — freeze ordering + fund tracing
    """
    G = build_hetero_graph(request)
    results = real_inference(G, request)
    return results

@app.post("/api/predict")
def predict(request: IntakeRequest):
    """Single transaction prediction endpoint, same response as /api/analyze."""
    G = build_hetero_graph(request)
    results = real_inference(G, request)
    return results

@app.post("/api/batch-predict")
def batch_predict(requests: List[IntakeRequest]):
    """Batch prediction for multiple intake requests. Returns list of prediction results."""
    batch_results = []
    for req in requests:
        G = build_hetero_graph(req)
        res = real_inference(G, req)
        batch_results.append(res)
    return {"predictions": batch_results}


@app.post("/api/external-check")
def external_check(account_ids: list[str]):
    """
    Standalone external intelligence lookup.
    Checks accounts against I4C, NCRP, watchlists (stub).
    """
    from external_intel import batch_check
    results = batch_check(account_ids)
    return {
        acct: {
            "watchlist_hits": len(e.watchlist_hits),
            "risk_uplift": e.risk_uplift,
            "i4c_status": e.i4c_status,
            "known_mule": e.known_mule,
            "details": [h.dict() for h in e.watchlist_hits],
        }
        for acct, e in results.items()
    }


_MODEL_METRICS_CACHE: Dict[str, Any] = {"data": None, "computed_at": None}


@app.get("/api/models")
def model_info():
    """
    Return metadata about loaded ML models (Layer 10 — Governance).
    Includes cached held-out evaluation metrics (precision/recall/F1/FPR) so
    this endpoint reflects real model quality, not just "a .pkl file exists".
    """
    from ml_models import get_model_metadata
    metadata = get_model_metadata()

    if _MODEL_METRICS_CACHE["data"] is None:
        _MODEL_METRICS_CACHE["data"] = evaluate_on_held_out()
        _MODEL_METRICS_CACHE["computed_at"] = datetime.utcnow().isoformat()

    metadata["held_out_evaluation"] = {
        **_MODEL_METRICS_CACHE["data"],
        "cached_at": _MODEL_METRICS_CACHE["computed_at"],
        "note": "Computed once per server run on a seeded held-out synthetic set (seed=99, disjoint from training seed=42). Call /api/v1/metrics for a fresh run.",
    }
    return metadata


@app.post("/api/v1/detect")
async def run_detection(
    token: str = Depends(verify_jwt),
    n_accounts: int = DEFAULT_TEST_ACCOUNTS,
    mule_ratio: float = DEFAULT_MULE_RATIO,
    threshold: float = DEFAULT_THRESHOLD,
    include_ground_truth: bool = True,
    seed: int = DEFAULT_SEED,
):
    """
    Run the full merchant payout demo pipeline on synthetic Razorpay-style data.
    Returns scores, explanations, clusters, false-positive cost, and audit trail.
    """
    graph, labels = generate_razorpay_payout_graph(
        n_beneficiaries=n_accounts,
        mule_ratio=mule_ratio,
        seed=seed,
    )
    agent = MuleNetDetectionAgent(threshold=threshold)
    report = agent.run_pipeline(graph, ground_truth=labels if include_ground_truth else None)
    AUDIT_RUNS[report["run_id"]] = report
    return {"status": "success", "report": report}

@app.post("/api/v1/detect/advanced")
async def detect_advanced(
    token: str = Depends(verify_jwt),
    n_accounts: int = DEFAULT_TEST_ACCOUNTS,
    mule_ratio: float = DEFAULT_MULE_RATIO,
    threshold: float = DEFAULT_THRESHOLD,
    include_ground_truth: bool = True,
    seed: int = DEFAULT_SEED,
):
    """Advanced detection using EnsembleScorer and SHAP explanations.

    Returns calibrated ensemble risk scores and SHAP values for each account.
    """
    graph, labels = generate_razorpay_payout_graph(
        n_beneficiaries=n_accounts,
        mule_ratio=mule_ratio,
        seed=seed,
    )
    # Compute base features using existing utilities
    agent = MuleNetDetectionAgent(threshold=threshold)
    report = agent.run_pipeline(graph, ground_truth=labels if include_ground_truth else None)
    features = compute_demo_features(graph)
    from ml_models import get_ensemble_scorer, get_fast_path
    ensemble = get_ensemble_scorer().predict(features)
    shap_vals = get_fast_path().shap_explain(features)
    report["ensemble_score"] = ensemble
    report["shap_explanations"] = shap_vals
    AUDIT_RUNS[report["run_id"]] = report
    return {"status": "success", "report": report}


@app.get("/api/v1/metrics")
async def get_metrics(
    token: str = Depends(verify_jwt),
    threshold: float = DEFAULT_THRESHOLD,
    n_test: int = DEFAULT_TEST_ACCOUNTS,
    mule_ratio: float = DEFAULT_MULE_RATIO,
    seed: int = 99,
    sweep: bool = False,
):
    """
    Return precision, recall, FPR, and false-positive cost on a held-out set.
    """
    if sweep:
        return {"status": "success", "threshold_sweep": threshold_sweep(n_test_accounts=n_test)}
    metrics = evaluate_on_held_out(
        threshold=threshold,
        n_test_accounts=n_test,
        mule_ratio=mule_ratio,
        seed=seed,
    )
    return {"status": "success", "metrics": metrics}


@app.get("/api/v1/audit/{run_id}")
async def get_audit_trail(run_id: str, token: str = Depends(verify_jwt)):
    """Return the structured audit trail and explanations for a prior detection run."""
    report = AUDIT_RUNS.get(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Audit run {run_id} not found")
    return {
        "status": "success",
        "run_id": run_id,
        "audit_log": report.get("audit_log", []),
        "explanations": report.get("explanations", {}),
        "cost_analysis": report.get("false_positive_cost_analysis", {}),
        "detection_summary": report.get("detection_summary", {}),
    }


@app.post("/api/v1/failure-demo")
async def failure_demo(n_accounts: int = 5, token: str = Depends(verify_jwt)):
    """
    Demonstrate graceful handling for cold-start accounts with zero transaction history.
    """
    cold_starts = generate_cold_start_accounts(n=n_accounts)
    graph = nx.DiGraph()
    for account in cold_starts:
        graph.add_node(account["account_id"], node_type="beneficiary", label="unknown")

    features = compute_demo_features(graph, cold_start_accounts=cold_starts)
    agent = MuleNetDetectionAgent()
    failures = agent.handle_cold_starts(features)
    agent._log("FAILURE_DEMO", f"Applied cold-start fallback to {len(failures)} accounts.")

    report = {
        "run_id": agent.run_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cold_start_accounts": cold_starts,
        "features": features,
        "graceful_failures": failures,
        "audit_log": agent.audit_log,
        "status": "success",
    }
    AUDIT_RUNS[agent.run_id] = report
    return {"status": "success", "report": report}


@app.get("/api/graph/query")
def query_graph(account_id: str):
    """
    Explore the live stateful graph database (Gap 2).
    Returns the neighborhood network of the given account node.
    """
    from neo4j_store import get_neo4j_graph
    neo4j_graph = get_neo4j_graph()
    if neo4j_graph.enabled:
        result = neo4j_graph.get_neighborhood(account_id)
        if result and len(result.get("nodes", [])) > 0:
            return result

    from graph_builder import GLOBAL_GRAPH
    node_name = f"account:{account_id}"
    
    if not GLOBAL_GRAPH.has_node(node_name):
        return {"status": "error", "message": f"Account {account_id} not found in live Graph Store."}
        
    # Get neighbors within 2 hops
    neighbors = {node_name}
    current_hop = {node_name}
    for _ in range(2):
        next_hop = set()
        for node in current_hop:
            for succ in GLOBAL_GRAPH.successors(node):
                if succ.startswith("account:") or succ.startswith("device:"):
                    next_hop.add(succ)
            for pred in GLOBAL_GRAPH.predecessors(node):
                if pred.startswith("account:") or pred.startswith("device:"):
                    next_hop.add(pred)
        neighbors.update(next_hop)
        current_hop = next_hop
        
    subgraph_nodes = []
    subgraph_edges = []
    
    for n in neighbors:
        n_type = GLOBAL_GRAPH.nodes[n].get("node_type", "account")
        subgraph_nodes.append({
            "id": n.split(":")[-1],
            "type": n_type,
            "details": GLOBAL_GRAPH.nodes[n]
        })
        
    for u, v, data in GLOBAL_GRAPH.edges(data=True):
        if u in neighbors and v in neighbors:
            if data.get("edge_type") == "sent_to":
                subgraph_edges.append({
                    "from": u.split(":")[-1],
                    "to": v.split(":")[-1],
                    "amount": data.get("amount", 0.0),
                    "timestamp": data.get("timestamp", ""),
                    "utr": data.get("utr", "")
                })
            elif data.get("edge_type") == "uses_device":
                subgraph_edges.append({
                    "from": u.split(":")[-1],
                    "to": v.split(":")[-1],
                    "type": "device_link"
                })
                
    return {
        "status": "success",
        "account_id": account_id,
        "nodes": subgraph_nodes,
        "edges": subgraph_edges
    }


from fastapi import Header
from typing import Optional
import os

@app.post("/api/governance/retrain")
def retrain_models(authorization: Optional[str] = Header(None)):
    """
    Retrain ML models using investigator feedback from resolved cases.
    Forwards user JWT token to retrieve resolved cases from Spring Boot.
    """
    # Try delegating to Celery task queue if Redis is configured
    if os.getenv("REDIS_HOST"):
        try:
            from celery_app import retrain_models_task
            task = retrain_models_task.delay(authorization)
            return {
                "status": "success",
                "message": "Asynchronous model retraining task dispatched to Celery worker queue.",
                "task_id": task.id
            }
        except Exception as e:
            print(f"[Main] Celery queue dispatch failed: {e}. Falling back to synchronous retraining.")

    import requests
    import json
    import networkx as nx
    from ml_models import get_fast_path, get_gnn_scorer, get_model_metadata, get_anomaly_detector
    
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8080")
    headers = {"Authorization": authorization} if authorization else {}
    try:
        response = requests.get(f"{backend_url}/api/cases/feedback", headers=headers, timeout=10)
        if response.status_code != 200:
            return {"status": "error", "message": f"Failed to fetch feedback from backend: {response.text}"}
        cases = response.json()
    except Exception as e:
        return {"status": "error", "message": f"Could not connect to Spring Boot backend: {str(e)}"}
        
    feedback_samples = []
    feedback_graphs = []
    
    for c in cases:
        status = c.get("status")
        # Confirmed fraud/mule = 1, False positive / dismissed = 0
        label = 1 if status in ["FROZEN", "CLOSED"] else 0
        
        ml_resp_str = c.get("mlResponse")
        if not ml_resp_str:
            continue
            
        try:
            ml_data = json.loads(ml_resp_str)
        except Exception:
            continue
            
        ranking = ml_data.get("recovery_ranking", [])
        edges = ml_data.get("suspicious_edges", [])
        
        # 1. Build XGBoost feedback samples
        for item in ranking:
            feats = [
                item.get("out_degree", 0),
                item.get("in_degree", 0),
                item.get("total_sent", 0),
                item.get("total_recv", 0),
                item.get("pass_through_rate", 0),
                item.get("fan_out_ratio", 0),
                item.get("counterparty_entropy", 0),
                item.get("share_of_total_flow", 0)
            ]
            feedback_samples.append({"features": feats, "label": label})
            
        # 2. Build GNN feedback graph
        if ranking and edges:
            G_case = nx.DiGraph()
            node_idx = {}
            X_case = []
            y_case = []
            
            for idx, item in enumerate(ranking):
                node_id = item.get("account_id")
                G_case.add_node(node_id)
                node_idx[node_id] = idx
                
                pr = item.get("topology_score", 0) / 300.0  # approximate scaling
                deg = (item.get("out_degree", 0) + item.get("in_degree", 0)) / max(2 * len(ranking), 1)
                bw = item.get("topology_score", 0) / 200.0
                
                feats = [
                    item.get("out_degree", 0),
                    item.get("in_degree", 0),
                    item.get("total_sent", 0) / 100000,
                    item.get("total_recv", 0) / 100000,
                    item.get("pass_through_rate", 0),
                    item.get("fan_out_ratio", 0),
                    item.get("counterparty_entropy", 0),
                    item.get("share_of_total_flow", 0),
                    pr, deg, bw
                ]
                X_case.append(feats)
                y_case.append(label)
                
            for edge in edges:
                u = edge.get("from")
                v = edge.get("to")
                amt = edge.get("amount", 1.0)
                if G_case.has_node(u) and G_case.has_node(v):
                    G_case.add_edge(u, v, amount=amt)
                    
            feedback_graphs.append((G_case, X_case, y_case))
            
    # Trigger model retraining
    fast_path = get_fast_path()
    fast_path.retrain(feedback_samples)
    
    gnn = get_gnn_scorer()
    gnn.retrain(feedback_graphs)

    ad = get_anomaly_detector()
    ad.retrain(feedback_samples)
    
    return {
        "status": "success",
        "message": f"Successfully retrained models on {len(cases)} resolved investigator cases.",
        "samples_trained": len(feedback_samples),
        "graphs_trained": len(feedback_graphs),
        "models": get_model_metadata()
    }


from preprocess import build_live_features, FEATURE_COLS
import os as _os
# normalization stats saved by the Kaggle training run (train-only stats)
_norm_stats_file = _os.path.join(_os.path.dirname(__file__), "trained_models", "norm_stats.json")
if _os.path.exists(_norm_stats_file):
    NORM_STATS = json.load(open(_norm_stats_file))
else:
    NORM_STATS = {"total_flow": 5238281033.0, "max_entropy": 14.5}


def generate_txn_dict():
    import random
    import datetime
    
    # Pre-defined pools of accounts and devices to simulate real-world overlaps
    accounts = [f"AC-{i}" for i in range(1001, 1030)] + ["AC-VICTIM", "AC-MERCHANT", "AC-ECOM", "AC-PG-GATEWAY"]
    devices = [f"DEV-{i}" for i in range(50001, 50015)]
    
    # 20% chance of an anomalous transaction (large amount or mule-like)
    is_anomaly = random.random() < 0.20
    
    sender = random.choice(accounts)
    receiver = random.choice([a for a in accounts if a != sender])
    
    if is_anomaly:
        amount = round(random.uniform(50000, 250000), 2)
        # Anomalies often share the same device or hit the merchant/mule pattern
        device = random.choice(devices[:3]) # more collisions
    else:
        amount = round(random.uniform(100, 15000), 2)
        device = random.choice(devices)
        
    utr = f"UTR{random.randint(100000000000, 999999999999)}"
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    
    # Let's perform a lightweight live check to see what the simulated risk would be
    # Build a mini features dict to calculate an inline risk score
    # (So the frontend can show a Flink/XGBoost/GNN live risk evaluation)
    from ml_models import get_fast_path, get_anomaly_detector
    
    mock_rolling = {
        "out_degree": random.randint(1, 6) if is_anomaly else random.randint(1, 2),
        "in_degree": random.randint(1, 4) if is_anomaly else random.randint(1, 2),
        "total_sent": amount if is_anomaly else amount * 0.1,   # RAW rupees — same as real window
        "total_recv": amount,
        "out_cp": random.randint(2, 5) if is_anomaly else 1,
        "inc_cp": random.randint(1, 3) if is_anomaly else random.randint(1, 2),
        "cp_entropy_raw": 1.5 if is_anomaly else 0.2,
    }
    mock_features = build_live_features(mock_rolling, NORM_STATS["total_flow"], NORM_STATS["max_entropy"])
    
    fp = get_fast_path()
    ad = get_anomaly_detector()
    
    # predict takes a dict of {acct_id: features_dict}
    fp_prob = fp.predict({receiver: mock_features}).get(receiver, 0.0)
    ad_prob = ad.predict({receiver: mock_features}).get(receiver, 0.0)
    
    # Sigmoidal combination
    raw_score = fp_prob * 45 + ad_prob * 35 + (30 if is_anomaly else 5)
    
    from ml_models import calibrate_score
    calibrated_score = calibrate_score(raw_score)
    
    return {
        "utr": utr,
        "amount": amount,
        "timestamp": ts,
        "sender_account": sender,
        "receiver_account": receiver,
        "device_id": device,
        "risk_evaluation": {
            "fast_path_score": fp_prob,
            "anomaly_score": ad_prob,
            "calibrated_risk_score": calibrated_score,
            "anomaly_reason": "Suspicious rapid cash-out" if is_anomaly and calibrated_score > 60 else "Normal profile"
        }
    }

@app.get("/api/stream/next")
def stream_next():
    """
    Simulates a live incoming UPI transaction event on the Kafka topic (Gap 1).
    Dynamically generates accounts, devices, amounts, and flags anomalies.
    """
    return generate_txn_dict()

@app.get("/api/stream/subscribe")
async def stream_subscribe():
    async def gen():
        while True:
            txn = generate_txn_dict()
            yield f"data: {json.dumps(txn)}\n\n"
            await asyncio.sleep(1.5)
    return StreamingResponse(gen(), media_type="text/event-stream")
