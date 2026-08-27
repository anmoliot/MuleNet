import sys
import os

# Add ml_service root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_loader import load_real_data

def _get_training_data():
    """Return X, y for training. Prefer real data if REAL_DATA_PATH is set."""
    try:
        return load_real_data()
    except Exception:
        # fall back to synthetic data
        return _generate_training_data()


import mlflow

    # Start MLflow run
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000"))
    with mlflow.start_run(run_name="XGBoost FastPath Training"):
        # Log parameters
        mlflow.log_param("model", "XGBoost FastPath")
        mlflow.log_param("n_estimators", 200)
        mlflow.log_param("max_depth", 5)
        mlflow.log_param("learning_rate", 0.1)

        # Train model (existing code)
        model = FastPathModel()
        model._train()

        # Log metrics (using synthetic test set for demonstration)
        X_test, y_test = _generate_training_data(n_samples=2000, seed=99)
        X_scaled = model.scaler.transform(X_test)
        preds = model.model.predict_proba(X_scaled)[:, 1]
        from sklearn.metrics import roc_auc_score, average_precision_score
        roc_auc = roc_auc_score(y_test, preds)
        pr_auc = average_precision_score(y_test, preds)
        mlflow.log_metric("roc_auc", roc_auc)
        mlflow.log_metric("pr_auc", pr_auc)

        # Log model artifact
        mlflow.sklearn.log_model(model.model, "model")
        mlflow.log_artifact("trained_models/fast_path_scaler.pkl", "scaler")

    print("\nTraining complete. Artifacts saved to `trained_models/` and logged to MLflow.")

if __name__ == "__main__":
    main()
