import sys
import os
import numpy as np
from sklearn.ensemble import IsolationForest

import mlflow

# Add ml_service root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml_models import _generate_training_data
from data_loader import load_real_data

def main():
    print("=== Training Isolation Forest Model ===")
    try:
    X, _ = load_real_data()
except Exception:
    X, _ = _generate_training_data(n_samples=3000, seed=42)
    # Use the same scaler as FastPath for consistency (if needed)
    from ml_models import FastPathModel
    scaler = FastPathModel().scaler
    X_scaled = scaler.transform(X)

    iso = IsolationForest(contamination=0.1, random_state=42)
    iso.fit(X_scaled)
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
with mlflow.start_run(run_name="IsolationForest Training"):
    mlflow.log_param("model", "IsolationForest")
    mlflow.log_param("contamination", 0.1)
    # Save model
    import joblib, pathlib
    model_path = pathlib.Path('trained_models/isolation_forest.pkl')
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(iso, model_path)
    mlflow.sklearn.log_model(iso, "model")
    mlflow.log_artifact(str(model_path), "model_artifact")
    print(f"Isolation Forest trained and saved to {model_path}")
    
    print(f"Isolation Forest trained and saved to {model_path}")

if __name__ == "__main__":
    main()
