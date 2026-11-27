"""Evaluate an immutable candidate with a frozen validation operating point."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mulenet_core.artifacts import write_manifest
from mulenet_core.environment import package_version
from mulenet_core.io import canonical_json
from mulenet_core.models import ModelBundle
from mulenet_core.schema import FeatureConfig
from sklearn.calibration import calibration_curve
from sklearn.metrics import precision_recall_curve, roc_curve
from training.experiment import load_input, prepare
from training.train_gnn import predict_graphs

from eval.adversarial import evaluate_attacks
from eval.lead_time import terminal_coverage
from eval.metrics import recall_interval, summarize

ROOT = Path(__file__).resolve().parents[2]


def figures(truth, scores, directory, prefix):
    directory.mkdir(parents=True, exist_ok=True)
    precision, recall, _ = precision_recall_curve(truth, scores)
    fpr, tpr, _ = roc_curve(truth, scores)
    actual, predicted = calibration_curve(truth, scores, n_bins=10)
    for name, x, y, xlabel, ylabel in (
        ("pr", recall, precision, "Recall", "Precision"),
        ("roc", fpr, tpr, "False-positive rate", "True-positive rate"),
        ("reliability", predicted, actual, "Predicted probability", "Observed positive fraction"),
    ):
        fig, ax = plt.subplots(figsize=(5.5, 4))
        ax.plot(x, y, marker=".", color="#177d71")
        if name == "reliability":
            ax.plot([0, 1], [0, 1], color="#888888", linestyle="--")
        ax.set(xlabel=xlabel, ylabel=ylabel, xlim=(0, 1), ylim=(0, 1))
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(directory / f"{prefix}-{name}.png", dpi=140)
        plt.close(fig)


def evaluate(
    dataset_name, data_path, split_name, model_directory, output, allow_synthetic=False, attacks=True, currency="INR"
):
    config = FeatureConfig(currency=currency)
    dataset = load_input(dataset_name, data_path, allow_synthetic)
    bundle = ModelBundle(model_directory, config, allow_synthetic=allow_synthetic)
    data_hash = hashlib.sha256(canonical_json(dataset.model_dump(mode="json"))).hexdigest()
    if bundle.manifest["data_hash"] != data_hash or bundle.training["split"] != split_name:
        raise ValueError("Evaluation data/split do not match the trained experiment")
    split, graphs = prepare(
        dataset,
        split_name,
        config,
        horizon=bundle.training.get("label_horizon_seconds", 21600),
        observation_bounds=bundle.training.get("observation_bounds"),
    )
    rows = split.test
    raw_gnn = predict_graphs(bundle.gnn, graphs["test"])
    scores = bundle.predict([row.features for row in rows], [raw_gnn[(row.account_id, row.as_of)] for row in rows])
    truth = np.asarray([row.label for row in rows])
    operating_model = bundle.training.get("selected_model", bundle.training["default_deep_path"])
    operating_scores = scores[operating_model]
    operating_threshold = bundle.training["thresholds"][operating_model]
    days = max(1.0, (max(r.as_of for r in rows) - min(r.as_of for r in rows) + 86400) / 86400)
    metrics = {
        name: summarize(
            truth, score, bundle.training["thresholds"].get(name), days=days, calibrated=name != "anomaly_signal"
        )
        for name, score in scores.items()
    }
    metadata = {
        "dataset": dataset_name,
        "data_provenance": dataset.data_provenance,
        "data_hash": data_hash,
        "split": split_name,
        "feature_schema_hash": bundle.manifest["feature_schema_hash"],
        "model_version": bundle.manifest["model_version"],
        "operating_point": bundle.training["threshold_selection"],
        "default_deep_path_selected_on_val": bundle.training["default_deep_path"],
        "operating_model": operating_model,
        "environment": {
            "python": platform.python_version(),
            "packages": {
                name: package_version(name) for name in ("numpy", "scikit-learn", "xgboost", "torch", "torch-geometric")
            },
        },
        "limitations": bundle.training["limitations"]
        + [
            "Row-bootstrap CIs ignore ring/account dependence",
            "Account-day forecast, not contemporaneous transaction classification",
            "Cash-out lead-time unavailable without cash-out annotations",
        ],
    }
    typology = {}
    prediction = operating_scores >= operating_threshold
    for name in sorted({e.typology for e in dataset.transactions if e.fraud and e.typology}):
        hits = []
        for row, hit in zip(rows, prediction, strict=True):
            if any(
                e.fraud
                and e.typology == name
                and row.as_of < e.ts <= row.label_end
                and row.account_id in (e.source, e.target)
                for e in dataset.transactions
            ):
                hits.append(hit)
        typology[name] = recall_interval(hits)
    if split_name == "entity":
        from mulenet_core.splits import entity_partitions, partition_events

        events = partition_events(dataset.transactions, entity_partitions(dataset.transactions), "test")
    else:
        events = dataset.transactions
    adversarial = (
        evaluate_attacks(bundle, events, rows, dataset.accounts, operating_scores, operating_model)
        if attacks
        else {"status": "not_run", "reason": "explicit --skip-attacks"}
    )
    ledger_path = data_path.with_suffix(".cashouts.json")
    ledger = None
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_bytes())
        if ledger["data_hash"] != data_hash:
            raise ValueError("Terminal ledger does not match the evaluated dataset")
    lead_time = (
        terminal_coverage(events, rows, operating_scores, operating_threshold, ledger["events"])
        if ledger
        else {"value": None, "ci95": None, "reason": "No independently defined terminal ledger supplied"}
    )
    cost_curve = []
    for threshold in np.linspace(0, 1, 11):
        measurement = summarize(truth, operating_scores, threshold, days=days)
        cost_curve.append(
            {
                "threshold": float(threshold),
                "what_if_only_not_threshold_selection": True,
                "assumed_false_freeze_cost_inr": measurement["metrics"]["assumed_false_freeze_cost_inr"],
                "recall": measurement["metrics"]["recall"],
                "terminal_coverage": terminal_coverage(events, rows, operating_scores, threshold, ledger["events"])
                if ledger
                else None,
            }
        )
    report = {
        "metadata": metadata,
        "models": metrics,
        "typology": typology,
        "adversarial": adversarial,
        "time_to_detect": lead_time,
        "cost_curve": cost_curve,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(report))
    prefix = f"{dataset_name}-{split_name}"
    for name, section in (
        ("ablation", metrics),
        ("typology", typology),
        ("adversarial", adversarial),
        (
            "calibration",
            {name: value["metrics"].get("ece") for name, value in metrics.items() if name != "anomaly_signal"},
        ),
    ):
        (output.parent / f"{name}-{prefix}.json").write_bytes(
            canonical_json({"metadata": metadata, "results": section})
        )
    prediction_path = output.parent / f"predictions-{prefix}.csv"
    with prediction_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["account_id", "as_of", "label", *scores])
        for index, row in enumerate(rows):
            writer.writerow(
                [row.account_id, row.as_of, row.label, *[float(values[index]) for values in scores.values()]]
            )
    figures(truth, operating_scores, output.parent / "figures", prefix)
    # Attach measured evidence and re-seal the candidate; model-version hashes only weights.
    (model_directory / "evaluation.json").write_bytes(canonical_json(report))
    write_manifest(model_directory, config, data_hash, model_directory / "evaluation.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["amlworld", "paysim", "sim"], required=True)
    parser.add_argument("--split", choices=["temporal", "entity"], required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--currency", default="INR")
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--skip-attacks", action="store_true")
    args = parser.parse_args()
    result = evaluate(
        args.dataset,
        args.data,
        args.split,
        args.models,
        args.out,
        args.allow_synthetic,
        not args.skip_attacks,
        args.currency,
    )
    print(json.dumps({"metadata": result["metadata"], "fusion": result["models"]["fusion"]}, indent=2))


if __name__ == "__main__":
    main()
