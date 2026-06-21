import json
import os
import requests
import networkx as nx
from celery import Celery

# Configure Celery with Redis broker/backend
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
celery = Celery(
    "mulenet_tasks",
    broker=f"redis://{REDIS_HOST}:6379/0",
    backend=f"redis://{REDIS_HOST}:6379/0"
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
)


@celery.task(name="tasks.retrain_models")
def retrain_models_task(authorization_header):
    print("[Celery] Starting model retraining task...")

    # Import locally inside the task to prevent circular dependencies
    from ml_models import get_fast_path, get_gnn_scorer, get_anomaly_detector, get_model_metadata
    from mlops import run_tracked_training

    # Fetch resolved cases from Spring Boot using the investigator's security token
    backend_url = os.getenv("BACKEND_API_URL", "http://localhost:8080")
    headers = {"Authorization": authorization_header} if authorization_header else {}
    
    try:
        response = requests.get(f"{backend_url}/api/cases/feedback", headers=headers, timeout=20)
        if response.status_code != 200:
            return {"status": "error", "message": f"Failed to fetch feedback from backend: {response.text}"}
        cases = response.json()
    except Exception as e:
        return {"status": "error", "message": f"Could not connect to Spring Boot backend: {str(e)}"}

    print(f"[Celery] Retraining on {len(cases)} resolved compliance cases.")
    feedback_samples = []
    feedback_graphs = []

    for c in cases:
        status = c.get("status")
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

        # 1. Build tabular feedback samples for XGBoost & Isolation Forest
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

        # 2. Build graph-native feedback samples for GNN
        if ranking and edges:
            G_case = nx.DiGraph()
            node_idx = {}
            X_case = []
            y_case = []

            for idx, item in enumerate(ranking):
                node_id = item.get("account_id")
                G_case.add_node(node_id)
                node_idx[node_id] = idx

                pr = item.get("topology_score", 0) / 300.0
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

    # Retrain model parameters
    print(f"[Celery] Retraining FastPath XGBoost on {len(feedback_samples)} samples...")
    get_fast_path().retrain(feedback_samples)

    print(f"[Celery] Retraining DeepPath GNN on {len(feedback_graphs)} custom graph patterns...")
    get_gnn_scorer().retrain(feedback_graphs)

    print(f"[Celery] Retraining Isolation Forest anomaly model...")
    get_anomaly_detector().retrain(feedback_samples)

    # Track metrics in MLflow if running
    try:
        run_tracked_training(model_name="Celery-Asynchronous-Retraining", force_retrain=False)
    except Exception as e:
        print(f"[Celery] MLflow logging skipped (service unconfigured): {e}")

    print("[Celery] Asynchronous retraining task finished successfully.")
    return {
        "status": "success",
        "samples_trained": len(feedback_samples),
        "graphs_trained": len(feedback_graphs),
        "models": get_model_metadata()
    }
