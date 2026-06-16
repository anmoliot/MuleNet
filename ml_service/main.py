"""
main.py — MuleNet ML Service
Graph-Native Fraud Decisioning Platform — FastAPI entry point
Full 11-layer architecture with real ML models.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from graph_builder import build_hetero_graph, real_inference, IntakeRequest, MODEL_VERSION, FUSION_WEIGHTS

app = FastAPI(
    title="MuleNet ML Engine",
    description="Graph-Native Fraud Decisioning — Real XGBoost + GNN Pipeline",
    version=MODEL_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/models")
def model_info():
    """Return metadata about loaded ML models (Layer 10 — Governance)."""
    from ml_models import get_model_metadata
    return get_model_metadata()


@app.get("/api/graph/query")
def query_graph(account_id: str):
    """
    Explore the live stateful graph database (Gap 2).
    Returns the neighborhood network of the given account node.
    """
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

@app.post("/api/governance/retrain")
def retrain_models(authorization: Optional[str] = Header(None)):
    """
    Retrain ML models using investigator feedback from resolved cases.
    Forwards user JWT token to retrieve resolved cases from Spring Boot.
    """
    import requests
    import json
    import networkx as nx
    from ml_models import get_fast_path, get_gnn_scorer, get_model_metadata, get_anomaly_detector
    
    headers = {"Authorization": authorization} if authorization else {}
    try:
        response = requests.get("http://localhost:8080/api/cases/feedback", headers=headers, timeout=10)
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


@app.get("/api/stream/next")
def stream_next():
    """
    Simulates a live incoming UPI transaction event on the Kafka topic (Gap 1).
    Dynamically generates accounts, devices, amounts, and flags anomalies.
    """
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
    
    # Compute mock features just for this txn
    mock_features = {
        "out_degree": random.randint(1, 6) if is_anomaly else random.randint(1, 2),
        "in_degree": random.randint(1, 4) if is_anomaly else random.randint(1, 2),
        "total_sent": amount if is_anomaly else amount * 0.1,
        "total_recv": amount,
        "pass_through_rate": 0.85 if is_anomaly else 0.15,
        "fan_out_ratio": 2.5 if is_anomaly else 0.5,
        "counterparty_entropy": 1.5 if is_anomaly else 0.2,
        "share_of_total_flow": 0.4 if is_anomaly else 0.05
    }
    
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

