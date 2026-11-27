"""Temporal transaction benchmark; outcome balances are a separate diagnostic."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import skops.io as sio
import xgboost as xgb
from mulenet_core.artifacts import sha256
from mulenet_core.calibration import calibrated_probabilities
from mulenet_core.io import canonical_json
from mulenet_core.models import load_skops
from mulenet_core.transaction_features import POST_TRANSFER_NAMES, PRE_TRANSFER_NAMES, transaction_features
from training.train_tabular import fit_calibrator, select_threshold, train_xgb

from eval.metrics import summarize
from eval.run_eval import figures

ROOT = Path(__file__).resolve().parents[2]


def run(path, directory, *, train=False):
    profile = json.loads((ROOT / "reports/profile-paysim.json").read_bytes())
    if sha256(path) != profile["sha256"]:
        raise ValueError("PaySim file differs from profiled content hash")
    n = profile["transactions"]
    matrix = np.empty((n, len(POST_TRANSFER_NAMES)), dtype=np.float32)
    labels, steps = np.empty(n, dtype=np.int8), np.empty(n, dtype=np.int32)
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        count = 0
        for count, row in enumerate(reader, 1):
            if row["isFraud"] not in {"0", "1"}:
                raise ValueError("Unknown transaction label")
            matrix[count - 1] = transaction_features(row, post_transfer=True)
            labels[count - 1], steps[count - 1] = int(row["isFraud"]), int(row["step"])
        if count != n:
            raise ValueError("Dataset row count changed")
    train_end = int(profile["minimum_time"] + (profile["maximum_time"] - profile["minimum_time"]) * 0.6)
    val_end = int(profile["minimum_time"] + (profile["maximum_time"] - profile["minimum_time"]) * 0.8)
    masks = {"train": steps < train_end, "val": (steps >= train_end) & (steps < val_end), "test": steps >= val_end}
    result = {
        "metadata": {
            "dataset": "PaySim",
            "data_provenance": "synthetic",
            "source_sha256": profile["sha256"],
            "task": "contemporaneous transaction classification, NOT future account/ring detection",
            "split": "temporal",
            "train_end_step_exclusive": train_end,
            "validation_end_step_exclusive": val_end,
            "counts": {part: int(mask.sum()) for part, mask in masks.items()},
            "seed": 42,
            "notebook_reference_reused_metrics": False,
            "topology_validation": False,
        },
        "models": {},
    }
    directory.mkdir(parents=True, exist_ok=True)
    for name, columns in (
        ("pre_transfer", len(PRE_TRANSFER_NAMES)),
        ("post_transfer_diagnostic", len(POST_TRANSFER_NAMES)),
    ):
        model_path, calibration_path = directory / f"{name}.ubj", directory / f"{name}.skops"
        policy_path = directory / f"{name}.json"
        if train:
            if any(p.exists() for p in (model_path, calibration_path, policy_path)):
                raise FileExistsError("Train PaySim into a new immutable directory")
            print(f"Training PaySim {name} on temporal TRAIN; early stopping on VAL", flush=True)
            model = train_xgb(
                matrix[masks["train"], :columns],
                labels[masks["train"]],
                matrix[masks["val"], :columns],
                labels[masks["val"]],
            )
            validation = model.predict_proba(matrix[masks["val"], :columns])[:, 1]
            calibration = fit_calibrator(validation, labels[masks["val"]])
            threshold = select_threshold(labels[masks["val"]], calibrated_probabilities(calibration, validation))
            model.save_model(model_path)
            sio.dump(calibration, calibration_path)
            policy_path.write_bytes(
                canonical_json(
                    {
                        "threshold": threshold,
                        "source_sha256": profile["sha256"],
                        "model_sha256": sha256(model_path),
                        "calibration_sha256": sha256(calibration_path),
                    }
                )
            )
        else:
            policy = json.loads(policy_path.read_bytes())
            if (
                policy["source_sha256"] != profile["sha256"]
                or sha256(model_path) != policy["model_sha256"]
                or sha256(calibration_path) != policy["calibration_sha256"]
            ):
                raise ValueError("PaySim artifact or data integrity mismatch")
            model = xgb.XGBClassifier()
            model.load_model(model_path)
            calibration = load_skops(calibration_path)
            threshold = policy["threshold"]
        diagnostics = {}
        test_scores = calibrated_probabilities(
            calibration, model.predict_proba(matrix[masks["test"], :columns])[:, 1], diagnostics
        )
        result["models"][name] = summarize(
            labels[masks["test"]], test_scores, threshold, days=max(1, (profile["maximum_time"] - val_end) / 24)
        )
        result["models"][name]["features"] = list(PRE_TRANSFER_NAMES if name == "pre_transfer" else POST_TRANSFER_NAMES)
        result["models"][name]["deployable_account_model"] = False
        result["models"][name]["availability"] = (
            "pre-transfer inputs only"
            if name == "pre_transfer"
            else "uses outcome balances; not pre-transfer detection evidence"
        )
        result["models"][name]["calibration_numerics"] = diagnostics
        figures(labels[masks["test"]], test_scores, ROOT / "reports/figures", f"paysim-{name}")
    result["metadata"]["limitations"] = [
        "Public simulated transactions, not real fraud outcomes",
        "Temporal split alone cannot validate topology",
        "Post-transfer diagnostic deliberately measures outcome-dependent features",
        "Row bootstrap ignores temporal/account dependence",
        "Cost parameters are assumptions, not INR losses observed in this unspecified-currency dataset",
    ]
    (ROOT / "reports/metrics-paysim-temporal.json").write_bytes(canonical_json(result))
    print(
        json.dumps(
            {
                "metadata": result["metadata"],
                "metrics": {name: value["metrics"] for name, value in result["models"].items()},
            },
            indent=2,
        )
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--train", action="store_true")
    args = parser.parse_args()
    run(args.data, args.models, train=args.train)


if __name__ == "__main__":
    main()
