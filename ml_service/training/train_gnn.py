import sys
import os

# Add ml_service root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml_models import GraphNeuralScorer, GNN_WEIGHTS_PATH, _generate_training_data
from data_loader import load_real_data
import mlflow

def main():
    # Load training data (real if available, otherwise synthetic)
    try:
        X, y = load_real_data()
    except Exception:
        X, y = _generate_training_data()

    # Set MLflow tracking URI (allow file store)
    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:///tmp/mlruns"))

    with mlflow.start_run(run_name="GNN DeepPath Training"):
        mlflow.log_param("model", "GNN DeepPath")
        # Train GNN (weights saved to trained_models/gnn_weights.pkl by the model class)
        gnn = GraphNeuralScorer()
        gnn._train()
        # Log the trained weights file as an artifact
        mlflow.log_artifact(str(GNN_WEIGHTS_PATH), "weights")

    print("\nTraining complete. Artefacts saved to `trained_models/` and logged to MLflow.")

if __name__ == "__main__":
    main()
