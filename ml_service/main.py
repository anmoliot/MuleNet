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
