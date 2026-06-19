"""
shap_explainer.py — MuleNet Explainability Engine
Provides SHAP (SHapley Additive exPlanations) and LIME (Local Interpretable
Model-agnostic Explanations) for the MuleNet fraud detection models.

For SHAP:
  - Uses TreeExplainer for XGBoost/GradientBoosting fast-path models
  - Falls back to permutation-based SHAP when TreeExplainer unavailable

For LIME:
  - Builds a local linear approximation around any high-risk account
  - Perturbs features, gets model predictions, fits weighted ridge regression

Produces structured JSON output for investigator dashboards.
"""

import numpy as np
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from ml_models import FastPathModel, FEATURE_COLS, get_fast_path


# ═══════════════════════════════════════════════════════════════════════════════
# SHAP EXPLAINER
# ═══════════════════════════════════════════════════════════════════════════════

class MuleNetSHAPExplainer:
    """
    Computes SHAP values for the FastPath XGBoost/GradientBoosting classifier.

    Tries to use the `shap` library first (TreeExplainer).
    Falls back to a mathematical permutation approximation if
    the library is not installed.
    """

    def __init__(self, fast_path: Optional[FastPathModel] = None):
        self.fast_path = fast_path or get_fast_path()
        self._shap_available = self._check_shap()

    def _check_shap(self) -> bool:
        try:
            import shap  # noqa: F401
            return True
        except ImportError:
            print("[SHAP] `shap` library not installed — using permutation approximation.")
            return False

    def explain(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Generate SHAP attributions for a single account's feature vector.

        Parameters
        ----------
        features : dict
            Mapping of feature_name -> value (same keys as FEATURE_COLS).

        Returns
        -------
        dict with keys:
            shap_values       : {feature: float}
            base_value        : float  (expected model output)
            prediction        : float  (actual model probability)
            explanation_text  : str
        """
        x_raw = np.array(
            [[features.get(col, 0.0) for col in FEATURE_COLS]],
            dtype=np.float64
        )
        x_scaled = self.fast_path.scaler.transform(x_raw)

        if self._shap_available:
            return self._shap_library_explain(x_scaled, features)
        else:
            return self._permutation_shap_explain(x_scaled, features)

    def _shap_library_explain(self, x_scaled: np.ndarray, features: Dict[str, float]) -> Dict[str, Any]:
        """Use official `shap` TreeExplainer."""
        import shap
        try:
            explainer = shap.TreeExplainer(self.fast_path.model)
            shap_vals = explainer.shap_values(x_scaled)
            # For binary classifiers shap_values returns list [neg_class, pos_class]
            if isinstance(shap_vals, list):
                sv = shap_vals[1][0]
                base = float(explainer.expected_value[1])
            else:
                sv = shap_vals[0]
                base = float(explainer.expected_value)
        except Exception:
            # Fallback for sklearn GradientBoosting
            explainer = shap.Explainer(self.fast_path.model, x_scaled)
            shap_obj = explainer(x_scaled)
            sv = shap_obj.values[0]
            base = float(shap_obj.base_values[0])

        shap_dict = {col: round(float(v), 6) for col, v in zip(FEATURE_COLS, sv)}
        prob = float(self.fast_path.model.predict_proba(x_scaled)[0, 1])

        top_factors = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        explanation = "Top drivers: " + ", ".join(
            f"{k} ({'↑' if v > 0 else '↓'} {abs(v):.4f})" for k, v in top_factors
        )

        return {
            "method": "TreeSHAP",
            "shap_values": shap_dict,
            "base_value": round(base, 6),
            "prediction": round(prob, 4),
            "explanation_text": explanation,
            "top_features": [k for k, _ in top_factors],
        }

    def _permutation_shap_explain(self, x_scaled: np.ndarray, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Permutation-based SHAP approximation (no external library).
        Estimates marginal contributions by masking each feature.
        """
        baseline = np.zeros_like(x_scaled)  # Baseline = all-zero vector
        pred_full = float(self.fast_path.model.predict_proba(x_scaled)[0, 1])
        pred_base = float(self.fast_path.model.predict_proba(baseline)[0, 1])

        shap_vals = {}
        for i, col in enumerate(FEATURE_COLS):
            x_missing = x_scaled.copy()
            x_missing[0, i] = 0.0
            pred_missing = float(self.fast_path.model.predict_proba(x_missing)[0, 1])
            shap_vals[col] = round(pred_full - pred_missing, 6)

        top_factors = sorted(shap_vals.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        explanation = "Top drivers (permutation SHAP): " + ", ".join(
            f"{k} ({'↑' if v > 0 else '↓'} {abs(v):.4f})" for k, v in top_factors
        )

        return {
            "method": "PermutationSHAP",
            "shap_values": shap_vals,
            "base_value": round(pred_base, 6),
            "prediction": round(pred_full, 4),
            "explanation_text": explanation,
            "top_features": [k for k, _ in top_factors],
        }

    def batch_explain(self, all_features: Dict[str, Dict[str, float]]) -> Dict[str, Dict]:
        """
        Explain multiple accounts at once.
        Returns {account_id: explanation_dict}.
        """
        results = {}
        for acct_id, feats in all_features.items():
            try:
                results[acct_id] = self.explain(feats)
            except Exception as e:
                results[acct_id] = {"error": str(e), "method": "failed"}
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# LIME EXPLAINER
# ═══════════════════════════════════════════════════════════════════════════════

class MuleNetLIMEExplainer:
    """
    Local Interpretable Model-Agnostic Explanations (LIME) for MuleNet.

    Algorithm:
    1. Define a neighbourhood around the instance by Gaussian perturbation.
    2. Score each perturbed sample with the black-box model.
    3. Fit a weighted ridge regression (weights = exp(-distance^2)).
    4. Return the linear coefficients as local feature importances.
    """

    def __init__(
        self,
        fast_path: Optional[FastPathModel] = None,
        n_samples: int = 200,
        sigma: float = 0.15,
        alpha: float = 1.0,
    ):
        self.fast_path = fast_path or get_fast_path()
        self.n_samples = n_samples
        self.sigma = sigma        # Gaussian perturbation std (in scaled space)
        self.alpha = alpha        # Ridge regularisation strength
        self._rng = np.random.RandomState(42)

    def explain(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Produce a LIME explanation for one account.

        Returns
        -------
        dict:
            lime_weights      : {feature: float}  (linear coefficient)
            intercept         : float
            r_squared         : float              (local fidelity)
            prediction        : float
            explanation_text  : str
        """
        x_raw = np.array(
            [[features.get(col, 0.0) for col in FEATURE_COLS]],
            dtype=np.float64
        )
        x_scaled = self.fast_path.scaler.transform(x_raw)[0]  # (n_features,)

        # 1. Sample neighbours in scaled space
        noise = self._rng.normal(0, self.sigma, (self.n_samples, len(FEATURE_COLS)))
        neighbours = x_scaled + noise  # (n_samples, n_features)

        # 2. Black-box predictions on neighbours
        probs = self.fast_path.model.predict_proba(neighbours)[:, 1]  # (n_samples,)

        # 3. Compute kernel weights (exponential distance)
        dists = np.linalg.norm(noise, axis=1)
        kernel_width = np.sqrt(len(FEATURE_COLS)) * 0.75
        weights = np.exp(-(dists ** 2) / (2 * kernel_width ** 2))

        # 4. Weighted Ridge Regression: X @ coef + intercept ≈ probs
        from sklearn.linear_model import Ridge
        lime_model = Ridge(alpha=self.alpha, fit_intercept=True)
        lime_model.fit(neighbours, probs, sample_weight=weights)

        coef_dict = {col: round(float(c), 6) for col, c in zip(FEATURE_COLS, lime_model.coef_)}

        # Local R² fidelity
        probs_pred = lime_model.predict(neighbours)
        ss_res = np.sum(weights * (probs - probs_pred) ** 2)
        ss_tot = np.sum(weights * (probs - np.average(probs, weights=weights)) ** 2)
        r2 = max(0.0, 1 - ss_res / (ss_tot + 1e-9))

        # Prediction for the original instance
        pred = float(self.fast_path.model.predict_proba(x_scaled.reshape(1, -1))[0, 1])

        top_factors = sorted(coef_dict.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        explanation = "LIME local model: " + ", ".join(
            f"{k} ({'↑' if v > 0 else '↓'} {abs(v):.4f})" for k, v in top_factors
        )

        return {
            "method": "LIME",
            "lime_weights": coef_dict,
            "intercept": round(float(lime_model.intercept_), 6),
            "r_squared": round(r2, 4),
            "prediction": round(pred, 4),
            "n_samples": self.n_samples,
            "explanation_text": explanation,
            "top_features": [k for k, _ in top_factors],
        }

    def batch_explain(self, all_features: Dict[str, Dict[str, float]]) -> Dict[str, Dict]:
        """Explain multiple accounts."""
        results = {}
        for acct_id, feats in all_features.items():
            try:
                results[acct_id] = self.explain(feats)
            except Exception as e:
                results[acct_id] = {"error": str(e), "method": "failed"}
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED RISK ATTRIBUTION REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_risk_attribution_report(
    account_id: str,
    features: Dict[str, float],
    risk_score: float,
    risk_level: str,
    fraud_probability: float,
    confidence: float,
    reason_codes: List[str],
) -> Dict[str, Any]:
    """
    Generate a full, investigator-ready Risk Attribution Report combining
    SHAP attributions, LIME weights, and structured reason codes.
    """
    shap_exp = MuleNetSHAPExplainer()
    lime_exp = MuleNetLIMEExplainer()

    shap_result = shap_exp.explain(features)
    lime_result = lime_exp.explain(features)

    # Rank features by average |SHAP| and |LIME| attribution
    combined_importance = {}
    for col in FEATURE_COLS:
        s = abs(shap_result["shap_values"].get(col, 0.0))
        l = abs(lime_result["lime_weights"].get(col, 0.0))
        combined_importance[col] = round((s + l) / 2, 6)

    ranked = sorted(combined_importance.items(), key=lambda x: x[1], reverse=True)

    return {
        "account_id": account_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "fraud_probability": fraud_probability,
        "model_confidence": confidence,
        "reason_codes": reason_codes,
        "shap_explanation": shap_result,
        "lime_explanation": lime_result,
        "combined_feature_importance": dict(ranked),
        "top_5_risk_drivers": [k for k, _ in ranked[:5]],
        "report_version": "1.0",
    }
