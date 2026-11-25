"""Manifest-verified model bundle; no auto-training or unsafe pickle loading."""

from pathlib import Path
import json

import numpy as np
import skops.io as sio
import torch
import xgboost as xgb

from .artifacts import verify_manifest
from .schema import FeatureConfig, feature_names
from .calibration import calibrated_probabilities

TRUSTED_TYPES = ["scipy.interpolate._interpolate.interp1d", "sklearn.tree._tree.Tree"]


def load_skops(path):
    unknown = set(sio.get_untrusted_types(file=path)) - set(TRUSTED_TYPES)
    if unknown:
        raise ValueError(f"Artifact contains unapproved types: {sorted(unknown)}")
    return sio.load(path, trusted=TRUSTED_TYPES)


class ModelBundle:
    def __init__(self, directory: Path, config: FeatureConfig = FeatureConfig(), *, allow_synthetic=False):
        self.manifest = verify_manifest(directory, config, allow_synthetic=allow_synthetic)
        self.config = config
        self.names = feature_names(config)
        self.directory = directory
        self.training = json.loads((directory / "training.json").read_bytes())
        self.tabular = xgb.XGBClassifier()
        self.tabular.load_model(directory / "tabular.ubj")
        self.graph_tabular = xgb.XGBClassifier()
        self.graph_tabular.load_model(directory / "tabular_graph.ubj")
        self.calibration = load_skops(directory / "calibration.skops")
        self.anomaly = load_skops(directory / "anomaly.skops")
        self.stack = load_skops(directory / "stack.skops")
        self.gnn = torch.jit.load(directory / "gnn.ts", map_location="cpu").eval()

    def matrix(self, features):
        if any(set(item) != set(self.names) for item in features):
            raise ValueError("Scoring input does not match the trained feature schema")
        result = np.asarray([[item[name] for name in self.names] for item in features], dtype=np.float64)
        if not np.isfinite(result).all():
            raise ValueError("Nonfinite model input")
        return result

    def components(self, features, gnn_probabilities):
        matrix = self.matrix(features)
        tab = self.tabular.predict_proba(matrix[:, self.training["tabular_indices"]])[:, 1]
        graph = self.graph_tabular.predict_proba(matrix)[:, 1]
        anomaly = -self.anomaly.score_samples(matrix)
        gnn = np.asarray(gnn_probabilities)
        return np.column_stack([graph, gnn, anomaly]), {"tabular": tab, "tabular_graph": graph, "gnn": gnn, "anomaly_signal": anomaly}

    def predict(self, features, gnn_probabilities):
        components, raw = self.components(features, gnn_probabilities)
        fusion = self.stack.predict_proba(components)[:, 1]
        raw["fusion"] = fusion
        return {name: calibrated_probabilities(self.calibration[name], value) if name in self.calibration else value for name, value in raw.items()}

    def explain_tabular(self, feature, limit=5):
        matrix = self.matrix([feature])
        contributions = self.graph_tabular.get_booster().predict(xgb.DMatrix(matrix), pred_contribs=True)[0, :-1]
        indices = np.argsort(-np.abs(contributions))[:limit]
        return [{"feature": self.names[i], "value": float(matrix[0, i]), "shap_log_odds": float(contributions[i])} for i in indices]
