import sys
import os

# Add ml_service root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml_models import GraphNeuralScorer, _generate_training_data
from data_loader import load_real_data
import mlflow

def _get_training_data():
    """Return X, y for training. Prefer real data if REAL_DATA_PATH is set."""
    try:
        return load_real_data()
    except Exception:
        return _generate_training_data()

def main():
    print("=== Training Graph Neural Network (GNN) DeepPath ===")
    # Start MLflow run
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    with mlflow.start_run(run_name="GNN DeepPath Training"):
        mlflow.log_param("model", "GNN DeepPath")
        # Training (real or synthetic data placeholder)
        gnn = GraphNeuralScorer()
        gnn._train()
        # Log model artifact
        mlflow.sklearn.log_model(gnn.model, "model")
        mlflow.log_artifact("trained_models/gnn_weights.pkl", "weights")
    print("\nTraining complete. Artifacts saved to `trained_models/` and logged to MLflow.")

if __name__ == "__main__":
    main()
