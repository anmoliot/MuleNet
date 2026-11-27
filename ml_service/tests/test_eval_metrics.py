import numpy as np
import pytest
from eval.metrics import recall_interval, summarize
from mulenet_core.transaction_features import transaction_features
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def test_transaction_features_reject_invalid_inputs():
    row = {
        "amount": "10",
        "oldbalanceOrg": "20",
        "oldbalanceDest": "0",
        "type": "TRANSFER",
        "step": "1",
        "newbalanceOrig": "10",
        "newbalanceDest": "10",
    }
    with pytest.raises(ValueError, match="money fields"):
        transaction_features(row | {"amount": "-1"})
    with pytest.raises(ValueError, match="kind"):
        transaction_features(row | {"type": "UNKNOWN"})
    with pytest.raises(ValueError, match="post-transfer"):
        transaction_features(row | {"newbalanceOrig": "nan"}, post_transfer=True)


def test_metric_point_estimates_match_sklearn_with_ties_and_bootstrap_repeats():
    truth = np.array([0, 1, 1, 0, 0, 1, 0, 1])
    scores = np.array([0.1, 0.8, 0.6, 0.6, 0.2, 0.6, 0.1, 0.9])
    report = summarize(truth, scores, 0.7, top_k=3)
    metrics = report["metrics"]
    assert metrics["roc_auc"]["value"] == pytest.approx(roc_auc_score(truth, scores))
    assert metrics["pr_auc"]["value"] == pytest.approx(average_precision_score(truth, scores))
    assert metrics["brier"]["value"] == pytest.approx(brier_score_loss(truth, scores))
    assert metrics["precision"]["value"] == 1
    assert metrics["recall"]["value"] == 0.5
    assert report == summarize(truth, scores, 0.7, top_k=3)
    assert len(metrics["pr_auc"]["ci95"]) == 2
    abstain = summarize(truth, scores, 1)
    assert abstain["metrics"]["precision"] == {"value": None, "ci95": None}
    assert abstain["metrics"]["recall"]["value"] == 0


def test_unknown_metrics_are_null_and_anomaly_not_claimed_calibrated():
    report = summarize([0, 0], [0.1, 0.2], 0.5)
    assert report["metrics"]["roc_auc"]["value"] is None
    anomaly = summarize([0, 1], [2.0, 3.0], None, calibrated=False)
    assert "ece" not in anomaly["metrics"] and "precision" not in anomaly["metrics"]
    assert recall_interval([-1, 0, 1])["value"] == 0
    assert recall_interval([])["value"] is None
    with pytest.raises(ValueError):
        summarize([0, 1], [0.1, 0.2], 0.5, resamples=10)


def test_pretransfer_features_ignore_outcome_balances():
    row = {
        "amount": "10",
        "oldbalanceOrg": "20",
        "oldbalanceDest": "5",
        "step": "3",
        "type": "TRANSFER",
        "newbalanceOrig": "10",
        "newbalanceDest": "15",
    }
    altered = {**row, "newbalanceOrig": "0", "newbalanceDest": "0"}
    assert transaction_features(row) == transaction_features(altered)
    assert transaction_features(row, post_transfer=True) != transaction_features(altered, post_transfer=True)


def test_terminal_paths_cannot_travel_backwards_in_time():
    from eval.lead_time import temporal_path
    from mulenet_core.schema import Transaction

    data = [
        Transaction(transaction_id="a", source="root", target="relay", ts=20, amount=10.0),
        Transaction(transaction_id="b", source="relay", target="sink", ts=10, amount=10.0),
    ]
    assert temporal_path(data, "root", 0, "b", 100) is None
    ordered = [data[0].model_copy(update={"ts": 5}), data[1]]
    assert temporal_path(ordered, "root", 0, "b", 100) == {"seconds_before_terminal": 10, "hops_before_terminal": 2}


def test_calibration_bounds_only_roundoff_not_arbitrary_bad_values():
    from mulenet_core.calibration import calibrated_probabilities

    class Calibrator:
        def predict(self, values):
            return values

    diagnostics = {}
    assert calibrated_probabilities(Calibrator(), [1.0000001192092896], diagnostics)[0] == 1
    assert diagnostics["bounded_values"] == 1
    with pytest.raises(ValueError, match="beyond"):
        calibrated_probabilities(Calibrator(), [1.01])
