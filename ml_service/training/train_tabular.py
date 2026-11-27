"""Train-only fitting; calibration and operating points use validation only."""

from __future__ import annotations

import numpy as np
import xgboost as xgb
from mulenet_core.calibration import calibrated_probabilities
from sklearn.ensemble import IsolationForest
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def train_xgb(x_train, y_train, x_val, y_val, seed=42):
    if len(np.unique(y_train)) != 2 or len(np.unique(y_val)) != 2:
        raise ValueError("Training and validation each require both classes")
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=1,
        colsample_bytree=1,
        tree_method="hist",
        n_jobs=1,
        random_state=seed,
        eval_metric="aucpr",
        early_stopping_rounds=12,
        scale_pos_weight=float((y_train == 0).sum() / (y_train == 1).sum()),
    )
    model.fit(x_train, y_train, eval_set=[(x_val, y_val)], verbose=False)
    return model


def fit_calibrator(probabilities, y_val):
    return IsotonicRegression(out_of_bounds="clip").fit(probabilities, y_val)


def select_threshold(y_val, probabilities, max_fpr=0.001):
    if not 0 <= max_fpr <= 1 or len(np.unique(y_val)) != 2:
        raise ValueError("Require a valid FPR target and both validation classes")
    candidates = np.append(np.unique(probabilities), np.nextafter(float(max(probabilities)), np.inf))
    feasible = []
    for threshold in candidates:
        predicted = probabilities >= threshold
        fpr = float(predicted[y_val == 0].mean())
        recall = float(predicted[y_val == 1].mean())
        if fpr <= max_fpr:
            feasible.append((recall, -fpr, float(threshold)))
    _, _, threshold = max(feasible)
    return threshold


def train_anomaly(x_train, seed=42):
    return IsolationForest(n_estimators=100, contamination="auto", random_state=seed, n_jobs=1).fit(x_train)


def train_stack(validation_components, y_val, seed=42):
    folds = min(5, int(np.bincount(y_val).min()))
    if folds < 2:
        raise ValueError("Validation stacking requires at least two examples of each class")
    meta = make_pipeline(StandardScaler(), LogisticRegression(C=1, max_iter=1000, random_state=seed))
    cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    # Base learners saw only TRAIN; these meta predictions also exclude each VAL row.
    oof = cross_val_predict(meta, validation_components, y_val, cv=cv, method="predict_proba")[:, 1]
    calibration = fit_calibrator(oof, y_val)
    meta.fit(validation_components, y_val)
    return meta, calibration, calibrated_probabilities(calibration, oof)
