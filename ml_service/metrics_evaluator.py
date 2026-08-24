"""Held-out evaluation metrics for the MuleNet merchant-risk demo."""

from typing import Any, Dict, List

from agent_loop import MuleNetDetectionAgent
from config import DEFAULT_MULE_RATIO, DEFAULT_TEST_ACCOUNTS, DEFAULT_THRESHOLD
from razorpay_simulator import generate_held_out_test_set


def evaluate_on_held_out(
    threshold: float = DEFAULT_THRESHOLD,
    n_test_accounts: int = DEFAULT_TEST_ACCOUNTS,
    mule_ratio: float = DEFAULT_MULE_RATIO,
    seed: int = 99,
) -> Dict[str, Any]:
    """Run the full agent on an unseen synthetic graph and return honest metrics."""
    graph, labels = generate_held_out_test_set(
        n_beneficiaries=n_test_accounts,
        mule_ratio=mule_ratio,
        seed=seed,
    )
    agent = MuleNetDetectionAgent(threshold=threshold)
    report = agent.run_pipeline(graph, ground_truth=labels)
    cost = report["false_positive_cost_analysis"]
    return {
        **cost,
        "run_id": report["run_id"],
        "graph_summary": report["graph_summary"],
        "detection_summary": report["detection_summary"],
        "clusters_detected": len(report["clusters"]),
        "audit_entries": len(report["audit_log"]),
    }


def threshold_sweep(thresholds: List[float] = None, n_test_accounts: int = DEFAULT_TEST_ACCOUNTS) -> Dict[str, Dict[str, Any]]:
    """Evaluate several thresholds for model‑selection trade‑off visibility."""
    thresholds = thresholds or [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    return {
        f"{threshold:.2f}": evaluate_on_held_out(threshold=threshold, n_test_accounts=n_test_accounts)
        for threshold in thresholds
    }


def export_metrics_csv(metrics: Dict[str, Any]) -> str:
    """Return a CSV representation of the metrics dictionary.

    The CSV contains a header row with metric names and a single data row.
    This helper is used by the frontend export button.
    """
    if not metrics:
        return ""
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(metrics.keys())
    writer.writerow([metrics[k] for k in metrics.keys()])
    return output.getvalue()
