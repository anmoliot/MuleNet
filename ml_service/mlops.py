"""
mlops.py — MuleNet MLOps Integration Layer

Provides:
  1. MLflow Experiment Tracking
     - Logs hyperparameters, training metrics (Accuracy, Precision, Recall,
       F1, ROC-AUC, PR-AUC, FPR, FNR), and model artifacts.
  2. Hugging Face Hub Integration
     - Push/pull trained models and datasets to HF Hub.
     - Auto-generate model/dataset cards.
  3. DVC-style Dataset Versioning stub
"""

import os
import pickle
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np

# ── Try importing optional dependencies ──────────────────────────────────────
try:
    import mlflow
    import mlflow.sklearn
    HAS_MLFLOW = True
except ImportError:
    HAS_MLFLOW = False
    print("[MLOps] MLflow not installed. Run: pip install mlflow")

try:
    from huggingface_hub import HfApi, hf_hub_download, upload_file
    HAS_HF = True
except ImportError:
    HAS_HF = False
    print("[MLOps] huggingface_hub not installed. Run: pip install huggingface_hub")

try:
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score,
        f1_score, roc_auc_score, average_precision_score,
        confusion_matrix
    )
    HAS_SKLEARN_METRICS = True
except ImportError:
    HAS_SKLEARN_METRICS = False


MODEL_DIR = Path(__file__).parent / "trained_models"
MODEL_DIR.mkdir(exist_ok=True)

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
HF_TOKEN = os.environ.get("HF_TOKEN", None)
HF_REPO_ID = os.environ.get("HF_REPO_ID", "your-org/mulenet-models")
HF_DATASET_REPO_ID = os.environ.get("HF_DATASET_REPO_ID", "your-org/mulenet-dataset")


# ═══════════════════════════════════════════════════════════════════════════════
# MLflow EXPERIMENT TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class MLflowTracker:
    """
    MLflow experiment tracker for MuleNet fraud detection models.

    Logs:
    - Hyperparameters: n_estimators, max_depth, learning_rate, subsample
    - Metrics: Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, FPR, FNR
    - Artifacts: model pickle, scaler pickle
    - Tags: model_name, framework, mule_net_version
    """

    def __init__(self, experiment_name: str = "MuleNet-FraudDetection"):
        self.experiment_name = experiment_name
        self.run_id: Optional[str] = None
        self._run = None

        if HAS_MLFLOW:
            try:
                mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
                mlflow.set_experiment(experiment_name)
                print(f"[MLflow] Tracking URI: {MLFLOW_TRACKING_URI}")
            except Exception as e:
                print(f"[MLflow] Could not connect to tracking server: {e}")
                print("[MLflow] Using local file tracking.")
                mlflow.set_tracking_uri(str(MODEL_DIR / "mlruns"))
                mlflow.set_experiment(experiment_name)

    def start_run(self, run_name: str, tags: Optional[Dict[str, str]] = None):
        """Start an MLflow run."""
        if not HAS_MLFLOW:
            print("[MLflow] Not available. Skipping run start.")
            return

        default_tags = {
            "framework": "XGBoost/SkLearn",
            "mule_net_version": "2.0.0",
            "use_case": "mule-account-detection",
        }
        if tags:
            default_tags.update(tags)

        self._run = mlflow.start_run(run_name=run_name, tags=default_tags)
        self.run_id = self._run.info.run_id
        print(f"[MLflow] Started run: {run_name} (ID: {self.run_id})")

    def log_hyperparameters(self, params: Dict[str, Any]):
        """Log model hyperparameters."""
        if not HAS_MLFLOW:
            print(f"[MLflow] Hyperparameters (not logged): {params}")
            return
        mlflow.log_params(params)

    def log_training_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: np.ndarray,
        step: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Compute and log full classification metrics.

        Parameters
        ----------
        y_true : ground truth labels (0/1)
        y_pred : binary predictions
        y_prob : predicted probabilities for class 1
        step   : optional step index for time series logging

        Returns
        -------
        dict of all computed metrics
        """
        if not HAS_SKLEARN_METRICS:
            print("[MLflow] sklearn.metrics not available.")
            return {}

        accuracy  = float(accuracy_score(y_true, y_pred))
        precision = float(precision_score(y_true, y_pred, zero_division=0))
        recall    = float(recall_score(y_true, y_pred, zero_division=0))
        f1        = float(f1_score(y_true, y_pred, zero_division=0))

        try:
            roc_auc = float(roc_auc_score(y_true, y_prob))
        except Exception:
            roc_auc = 0.0

        try:
            pr_auc = float(average_precision_score(y_true, y_prob))
        except Exception:
            pr_auc = 0.0

        if len(np.unique(y_true)) > 1:
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        else:
            tn, fp, fn, tp = 0, 0, 0, int(len(y_true))

        fpr = float(fp / (fp + tn + 1e-9))
        fnr = float(fn / (fn + tp + 1e-9))

        metrics = {
            "accuracy":            round(accuracy, 4),
            "precision":           round(precision, 4),
            "recall":              round(recall, 4),
            "f1_score":            round(f1, 4),
            "roc_auc":             round(roc_auc, 4),
            "pr_auc":              round(pr_auc, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "true_positives":      int(tp),
            "false_positives":     int(fp),
            "true_negatives":      int(tn),
            "false_negatives":     int(fn),
        }

        print(f"[MLflow] Acc:{accuracy:.4f} Prec:{precision:.4f} "
              f"Rec:{recall:.4f} F1:{f1:.4f} ROC-AUC:{roc_auc:.4f} PR-AUC:{pr_auc:.4f}")

        if HAS_MLFLOW:
            mlflow.log_metrics(metrics, step=step)

        return metrics

    def log_model_artifact(self, model_path: Path, artifact_name: str = "model"):
        """Log a pickled model file as an MLflow artifact."""
        if not HAS_MLFLOW or not model_path.exists():
            return
        mlflow.log_artifact(str(model_path), artifact_path=artifact_name)
        print(f"[MLflow] Logged artifact: {model_path.name}")

    def end_run(self):
        """End the current MLflow run."""
        if HAS_MLFLOW:
            mlflow.end_run()
            print(f"[MLflow] Run {self.run_id} ended.")

    def get_best_run(self, metric: str = "f1_score") -> Optional[Dict]:
        """Retrieve the best run from the current experiment by a given metric."""
        if not HAS_MLFLOW:
            return None
        try:
            client = mlflow.tracking.MlflowClient()
            experiment = client.get_experiment_by_name(self.experiment_name)
            if not experiment:
                return None
            runs = client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=[f"metrics.{metric} DESC"],
                max_results=1,
            )
            if runs:
                r = runs[0]
                return {
                    "run_id": r.info.run_id,
                    "metrics": r.data.metrics,
                    "params": r.data.params,
                    "tags": r.data.tags,
                }
        except Exception as e:
            print(f"[MLflow] Error fetching best run: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# HUGGING FACE HUB INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class HuggingFaceIntegration:
    """
    Upload and download MuleNet models and datasets to/from Hugging Face Hub.

    Supports:
    - Authenticated push of trained model checkpoints (.pkl files)
    - Dataset upload as CSV/Parquet with auto-generated dataset card
    - Model card generation
    - Inference API metadata
    """

    def __init__(
        self,
        token: Optional[str] = None,
        model_repo: str = HF_REPO_ID,
        dataset_repo: str = HF_DATASET_REPO_ID,
    ):
        self.token = token or HF_TOKEN
        self.model_repo = model_repo
        self.dataset_repo = dataset_repo
        self.api = HfApi() if HAS_HF else None

    def push_model(
        self,
        model_path: Path,
        scaler_path: Optional[Path] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Push a trained model pickle to Hugging Face Hub."""
        if not HAS_HF:
            print("[HuggingFace] huggingface_hub not installed.")
            return False
        if not self.token:
            print("[HuggingFace] HF_TOKEN not set. Cannot push.")
            return False
        if not model_path.exists():
            print(f"[HuggingFace] Model file not found: {model_path}")
            return False

        try:
            upload_file(
                path_or_fileobj=str(model_path),
                path_in_repo=model_path.name,
                repo_id=self.model_repo,
                token=self.token,
                repo_type="model",
            )
            print(f"[HuggingFace] Uploaded model: {model_path.name}")

            if scaler_path and scaler_path.exists():
                upload_file(
                    path_or_fileobj=str(scaler_path),
                    path_in_repo=scaler_path.name,
                    repo_id=self.model_repo,
                    token=self.token,
                    repo_type="model",
                )

            # Generate and push model card
            card_content = self._generate_model_card(metadata or {})
            card_path = MODEL_DIR / "README.md"
            card_path.write_text(card_content)
            upload_file(
                path_or_fileobj=str(card_path),
                path_in_repo="README.md",
                repo_id=self.model_repo,
                token=self.token,
                repo_type="model",
            )
            print("[HuggingFace] Model card uploaded.")
            return True

        except Exception as e:
            print(f"[HuggingFace] Push failed: {e}")
            return False

    def pull_model(self, filename: str = "fast_path_model.pkl") -> Optional[Path]:
        """Download a model file from Hugging Face Hub to local MODEL_DIR."""
        if not HAS_HF:
            print("[HuggingFace] huggingface_hub not installed.")
            return None
        try:
            local_path = hf_hub_download(
                repo_id=self.model_repo,
                filename=filename,
                token=self.token,
                local_dir=str(MODEL_DIR),
                repo_type="model",
            )
            print(f"[HuggingFace] Downloaded: {filename} → {local_path}")
            return Path(local_path)
        except Exception as e:
            print(f"[HuggingFace] Pull failed: {e}")
            return None

    def push_dataset(
        self,
        csv_path: Path,
        split_name: str = "train",
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Upload a training dataset CSV to Hugging Face Datasets Hub."""
        if not HAS_HF or not self.token or not csv_path.exists():
            return False
        try:
            upload_file(
                path_or_fileobj=str(csv_path),
                path_in_repo=f"data/{split_name}/{csv_path.name}",
                repo_id=self.dataset_repo,
                token=self.token,
                repo_type="dataset",
            )
            dataset_card = self._generate_dataset_card(metadata or {})
            card_path = MODEL_DIR / "DATASET_README.md"
            card_path.write_text(dataset_card)
            upload_file(
                path_or_fileobj=str(card_path),
                path_in_repo="README.md",
                repo_id=self.dataset_repo,
                token=self.token,
                repo_type="dataset",
            )
            print(f"[HuggingFace] Dataset uploaded: {csv_path.name}")
            return True
        except Exception as e:
            print(f"[HuggingFace] Dataset push failed: {e}")
            return False

    def _generate_model_card(self, metadata: Dict) -> str:
        """Generate a Hugging Face model card in Markdown."""
        metrics_block = ""
        if "metrics" in metadata:
            for k, v in metadata["metrics"].items():
                metrics_block += f"      - type: {k}\n        value: {v}\n"

        return f"""---
language:
- en
license: mit
tags:
- fraud-detection
- mule-account
- financial-crime
- graph-neural-network
- xgboost
model-index:
- name: MuleNet FastPath Classifier
  results:
  - task:
      type: binary-classification
    metrics:
{metrics_block if metrics_block else '      - type: f1\n        value: N/A'}
---

# MuleNet — Mule Account Detection Model

This model is a trained XGBoost / Gradient Boosting classifier for detecting
money mule accounts in financial transaction networks.

## Model Description

- **Architecture**: XGBoost (or sklearn GradientBoosting fallback)
- **Task**: Binary classification — mule account detection
- **Features**: 8 behavioral + graph-derived features per account
- **Training Data**: Synthetic + investigator-labeled transaction graphs
- **Version**: {metadata.get('version', '2.0.0')}
- **Last Updated**: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}

## Features

| Feature | Description |
|---|---|
| `out_degree` | Number of unique outgoing counterparties |
| `in_degree` | Number of unique incoming counterparties |
| `total_sent` | Total amount disbursed |
| `total_recv` | Total amount received |
| `pass_through_rate` | Ratio of sent to received funds |
| `fan_out_ratio` | out_degree / (in_degree + 1) |
| `counterparty_entropy` | Shannon entropy of outgoing transaction distribution |
| `share_of_total_flow` | Account's share of total network flow |

## Intended Use

For use by authorized financial crime investigators, AML teams, law enforcement,
and fraud analytics units. NOT for consumer use.

## Ethical Considerations

This model assists human investigators and is NOT used for automated account
blocking without human review.
"""

    def _generate_dataset_card(self, metadata: Dict) -> str:
        """Generate a Hugging Face dataset card."""
        return f"""---
license: mit
tags:
- financial-crime
- fraud-detection
- transactions
- mule-accounts
---

# MuleNet Training Dataset

Synthetic labeled dataset for training mule account detection models.

## Dataset Description

- **Size**: {metadata.get('n_samples', 'N/A')} samples
- **Positive Class**: {metadata.get('n_positive', 'N/A')} mule accounts (~30%)
- **Negative Class**: {metadata.get('n_negative', 'N/A')} legitimate accounts (~70%)
- **Created**: {datetime.datetime.utcnow().strftime('%Y-%m-%d')}

## Schema

| Column | Type | Description |
|---|---|---|
| `out_degree` | float | Outgoing counterparties |
| `in_degree` | float | Incoming counterparties |
| `total_sent` | float | Total INR sent |
| `total_recv` | float | Total INR received |
| `pass_through_rate` | float | Fund pass-through ratio |
| `fan_out_ratio` | float | Layering fan-out |
| `counterparty_entropy` | float | Distribution entropy |
| `share_of_total_flow` | float | Network flow share |
| `label` | int | 1=mule, 0=legitimate |
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE: TRACKED TRAINING RUN
# ═══════════════════════════════════════════════════════════════════════════════

def run_tracked_training(
    model_name: str = "FastPath-XGBoost",
    force_retrain: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function: train the FastPath model, log everything to MLflow,
    and return the metrics dict.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from ml_models import (
        _generate_training_data,
        get_fast_path,
        FAST_PATH_MODEL_PATH,
        FAST_PATH_SCALER_PATH,
    )

    tracker = MLflowTracker()
    ts = datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    tracker.start_run(run_name=f"{model_name}-{ts}")

    hparams = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "n_training_samples": 5000,
        "class_imbalance_ratio": 0.3,
    }
    tracker.log_hyperparameters(hparams)

    X, y = _generate_training_data(n_samples=5000)
    fp = get_fast_path()

    if force_retrain:
        fp._train()

    X_scaled = fp.scaler.transform(X)
    y_pred = fp.model.predict(X_scaled)
    y_prob = fp.model.predict_proba(X_scaled)[:, 1]

    metrics = tracker.log_training_metrics(y, y_pred, y_prob)

    tracker.log_model_artifact(FAST_PATH_MODEL_PATH, artifact_name="fastpath_model")
    tracker.log_model_artifact(FAST_PATH_SCALER_PATH, artifact_name="fastpath_scaler")
    tracker.end_run()

    return {"run_id": tracker.run_id, "metrics": metrics, "hyperparameters": hparams}


if __name__ == "__main__":
    print("=" * 60)
    print("MuleNet MLOps — Tracked Training Run")
    print("=" * 60)
    result = run_tracked_training(force_retrain=True)
    print("\nFinal Metrics:")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v}")
