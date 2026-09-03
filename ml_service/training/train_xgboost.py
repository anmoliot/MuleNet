import sys
import os
from pathlib import Path

# Add ml_service root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_loader import load_real_data
from ml_models import FastPathModel, _generate_training_data, FAST_PATH_MODEL_PATH, FAST_PATH_SCALER_PATH
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

    with mlflow.start_run(run_name="XGBoost FastPath Training"):
        mlflow.log_param("model", "XGBoost FastPath")
        mlflow.log_param("n_estimators", 200)
        mlflow.log_param("max_depth", 5)
        mlflow.log_param("learning_rate", 0.1)

        # Train model (this will save model and scaler files in ml_service/trained_models)
        model = FastPathModel()
        model._train()

        # Log metrics using synthetic test set for demonstration
        X_test, y_test = _generate_training_data(n_samples=2000, seed=99)
        X_scaled = model.scaler.transform(X_test)
        preds = model.model.predict_proba(X_scaled)[:, 1]
        from sklearn.metrics import roc_auc_score, average_precision_score
        roc_auc = roc_auc_score(y_test, preds)
        pr_auc = average_precision_score(y_test, preds)
        mlflow.log_metric("roc_auc", roc_auc)
        mlflow.log_metric("pr_auc", pr_auc)

        # Log model artifact files using absolute paths
        mlflow.log_artifact(str(FAST_PATH_MODEL_PATH), "model")
        mlflow.log_artifact(str(FAST_PATH_SCALER_PATH), "scaler")

    print("\nTraining complete. Artefacts saved to `trained_models/` and logged to MLflow.")

if __name__ == "__main__":
    main()
