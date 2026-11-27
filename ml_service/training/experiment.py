"""Reproducible preparation and training for temporal/entity experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import skops.io as sio
from mulenet_core.artifacts import write_manifest
from mulenet_core.calibration import calibrated_probabilities
from mulenet_core.drift_reference import DriftReference
from mulenet_core.io import canonical_json, load_amlworld, load_paysim, read_dataset
from mulenet_core.labels import Example, future_label, materialize
from mulenet_core.schema import Dataset, FeatureConfig, feature_names, feature_schema_hash
from mulenet_core.splits import Split, entity_partitions, entity_split, partition_events, temporal_split
from training.train_gnn import export_gnn, predict_graphs, snapshot_graph, train_gnn
from training.train_tabular import fit_calibrator, select_threshold, train_anomaly, train_stack, train_xgb


def load_input(dataset, path, allow_synthetic=False):
    if dataset == "sim":
        return read_dataset(path, allow_synthetic=allow_synthetic)
    if dataset == "amlworld" and path.suffix == ".json":
        receipt = json.loads(path.with_suffix(".receipt.json").read_bytes())
        if hashlib.sha256(path.read_bytes()).hexdigest() != receipt["cohort_sha256"]:
            raise ValueError("Cohort hash differs from its preparation receipt")
        result = Dataset.model_validate_json(path.read_bytes())
        if not result.source.startswith("amlworld-whole-component-cohort:"):
            raise ValueError("JSON is not a declared external benchmark cohort")
        return result
    events = load_amlworld(path) if dataset == "amlworld" else load_paysim(path)
    return Dataset(source=dataset, transactions=events)


def preflight_splits(dataset, split_name, horizon=21600, seed=42, observation_bounds=None, currency="INR"):
    start, end = observation_bounds or (
        min(e.ts for e in dataset.transactions),
        max(e.ts for e in dataset.transactions),
    )
    scoped = [event for event in dataset.transactions if event.currency == currency]
    nodes = sorted({e.source for e in scoped} | {e.target for e in scoped})
    first, related = {}, defaultdict(list)
    for event in scoped:
        first[event.source] = min(first.get(event.source, event.ts), event.ts)
        first[event.target] = min(first.get(event.target, event.ts), event.ts)
        related[event.source].append(event)
        if event.source != event.target:
            related[event.target].append(event)
    times = range(start + 86400 + 7200, end - horizon, 86400)
    points = [(node, ts) for ts in times for node in nodes if first[node] <= ts]
    assignment = entity_partitions(dataset.transactions, seed) if split_name == "entity" else None
    rows = []
    for account, as_of in points:
        label, ids = future_label(related[account], account, as_of, horizon, end, currency)
        rows.append(Example(account, as_of, as_of + horizon, label, {}, (), ids))
    if split_name == "temporal":
        return (
            temporal_split(rows, int(start + (end - start) * 0.6), int(start + (end - start) * 0.8)),
            points,
            (start, end),
        )
    if split_name == "entity":
        return (
            Split(
                *(tuple(row for row in rows if assignment[row.account_id] == part) for part in ("train", "val", "test"))
            ),
            points,
            (start, end),
        )
    raise ValueError("Unknown split")


def prepare(dataset: Dataset, split_name: str, config: FeatureConfig, horizon=21600, seed=42, observation_bounds=None):
    _, points, (start, end) = preflight_splits(dataset, split_name, horizon, seed, observation_bounds, config.currency)
    if len({account for account, _ in points}) > config.max_graph_nodes:
        raise ValueError(
            "Dataset exceeds full-snapshot node budget; select and disclose a whole-component cohort, never sample raw edges"
        )
    if split_name == "temporal":
        rows = materialize(dataset.transactions, points, horizon, end, config, dataset.accounts)
        split = temporal_split(rows, int(start + (end - start) * 0.6), int(start + (end - start) * 0.8))
        context = {name: dataset.transactions for name in ("train", "val", "test")}
    elif split_name == "entity":
        split = entity_split(dataset.transactions, points, horizon, end, config, dataset.accounts, seed)
        assignment = entity_partitions(dataset.transactions, seed)
        context = {name: partition_events(dataset.transactions, assignment, name) for name in ("train", "val", "test")}
    else:
        raise ValueError("Unknown split")
    graphs = {}
    for name in ("train", "val", "test"):
        groups = defaultdict(list)
        for row in getattr(split, name):
            groups[row.as_of].append(row)
        graphs[name] = {
            ts: snapshot_graph(context[name], rows, config, dataset.accounts) for ts, rows in groups.items()
        }
    return split, graphs


def train_experiment(
    dataset, dataset_name, split_name, directory, config, seed=42, epochs=30, horizon=21600, observation_bounds=None
):
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError("Train into a new immutable version directory")
    directory.mkdir(parents=True, exist_ok=True)
    preflight, _, bounds = preflight_splits(dataset, split_name, horizon, seed, observation_bounds, config.currency)
    if any(sum(row.label for row in getattr(preflight, part)) < 2 for part in ("train", "val")):
        raise ValueError(
            "Statistically insufficient training/validation positives; refusing to train or resample labels"
        )
    split, graphs = prepare(dataset, split_name, config, horizon=horizon, seed=seed, observation_bounds=bounds)
    names = feature_names(config)
    matrices = {
        part: np.asarray([[row.features[name] for name in names] for row in getattr(split, part)])
        for part in ("train", "val")
    }
    labels = {part: np.asarray([row.label for row in getattr(split, part)]) for part in ("train", "val")}
    topology = ("flow_hop", "cycle_count", "clustering", "pagerank")
    tabular_indices = [i for i, name in enumerate(names) if not any(term in name for term in topology)]
    tabular = train_xgb(
        matrices["train"][:, tabular_indices], labels["train"], matrices["val"][:, tabular_indices], labels["val"], seed
    )
    graph_tabular = train_xgb(matrices["train"], labels["train"], matrices["val"], labels["val"], seed)
    anomaly = train_anomaly(matrices["train"], seed)
    gnn, gnn_training = train_gnn(graphs["train"], graphs["val"], len(names), seed, epochs)
    val_gnn = predict_graphs(gnn, graphs["val"])
    gnn_prob = np.asarray([val_gnn[(row.account_id, row.as_of)] for row in split.val])
    raw = {
        "tabular": tabular.predict_proba(matrices["val"][:, tabular_indices])[:, 1],
        "tabular_graph": graph_tabular.predict_proba(matrices["val"])[:, 1],
        "gnn": gnn_prob,
    }
    meta_components = np.column_stack([raw["tabular_graph"], raw["gnn"], -anomaly.score_samples(matrices["val"])])
    stack, fusion_calibration, fusion_oof = train_stack(meta_components, labels["val"], seed)
    calibrators = {name: fit_calibrator(scores, labels["val"]) for name, scores in raw.items()}
    thresholds = {
        name: select_threshold(labels["val"], calibrated_probabilities(calibrators[name], scores))
        for name, scores in raw.items()
    }
    calibrators["fusion"] = fusion_calibration
    thresholds["fusion"] = select_threshold(labels["val"], fusion_oof)
    # The default deep path is decided on VAL only; the test cannot change it.
    recalls = {
        name: float(
            np.mean((calibrated_probabilities(calibrators[name], raw[name]) >= thresholds[name])[labels["val"] == 1])
        )
        for name in ("tabular_graph", "gnn")
    }
    default_deep = "gnn" if recalls["gnn"] > recalls["tabular_graph"] else "tabular_graph"
    training = {
        "dataset": dataset_name,
        "data_provenance": dataset.data_provenance,
        "split": split_name,
        "seed": seed,
        "label_horizon_seconds": horizon,
        "observation_bounds": list(bounds),
        "threshold_selection": "VAL only; maximize recall at empirical FPR <= 0.001",
        "thresholds": thresholds,
        "tabular_indices": tabular_indices,
        "default_deep_path": default_deep,
        "gnn": gnn_training,
        "rows": {part: len(getattr(split, part)) for part in ("train", "val", "test")},
        "stacking": "Base models fit on TRAIN; stratified out-of-fold meta predictions on VAL; isotonic on VAL OOF",
        "probability_numerics": "Only <=4 float32 ULP representation error is bounded to [0,1]; larger violations fail",
        "limitations": [
            "Synthetic data cannot establish bank effectiveness",
            "Small VAL has coarse FPR resolution",
            "Validation calibration and threshold reuse can overfit; TEST remains untouched during fitting",
        ],
    }
    tabular.save_model(directory / "tabular.ubj")
    graph_tabular.save_model(directory / "tabular_graph.ubj")
    sio.dump(calibrators, directory / "calibration.skops")
    sio.dump(anomaly, directory / "anomaly.skops")
    sio.dump(stack, directory / "stack.skops")
    # Keep test/validation rows out of monitoring's baseline, including score samples.
    train_gnn_predictions = predict_graphs(gnn, graphs["train"])
    train_neural = np.asarray([train_gnn_predictions[(row.account_id, row.as_of)] for row in split.train])
    train_graph = graph_tabular.predict_proba(matrices["train"])[:, 1]
    train_components = np.column_stack([train_graph, train_neural, -anomaly.score_samples(matrices["train"])])
    train_scores = {
        "tabular_graph": train_graph,
        "gnn": train_neural,
        "fusion": stack.predict_proba(train_components)[:, 1],
    }
    selected_rows = np.sort(
        np.random.default_rng(seed).choice(len(split.train), min(2048, len(split.train)), replace=False)
    )
    reference = DriftReference.model_validate_json(
        canonical_json(
            {
                "feature_schema_hash": feature_schema_hash(config),
                "feature_names": list(names),
                "source_split": "TRAIN",
                "data_provenance": dataset.data_provenance,
                "selection": "seeded uniform sample without replacement",
                "seed": seed,
                "train_rows": len(split.train),
                "features": matrices["train"][selected_rows].tolist(),
                "scores": {
                    name: calibrated_probabilities(calibrators[name], values)[selected_rows].tolist()
                    for name, values in train_scores.items()
                },
            }
        )
    )
    (directory / "drift-reference.json").write_bytes(canonical_json(reference.model_dump(mode="json")))
    export_gnn(gnn, next(iter(graphs["val"].values())), directory)
    training_path = directory / "training.json"
    training_path.write_bytes(canonical_json(training))
    data_hash = hashlib.sha256(canonical_json(dataset.model_dump(mode="json"))).hexdigest()
    write_manifest(directory, config, data_hash, training_path)
    return training


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["sim", "amlworld", "paysim"], required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--split", choices=["temporal", "entity"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--currency", default="INR")
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--horizon", type=int, default=21600)
    args = parser.parse_args()
    dataset = load_input(args.dataset, args.data, args.allow_synthetic)
    report = train_experiment(
        dataset,
        args.dataset,
        args.split,
        args.out,
        FeatureConfig(currency=args.currency),
        epochs=args.epochs,
        horizon=args.horizon,
    )
    reports = Path(__file__).resolve().parents[2] / "reports"
    reports.mkdir(exist_ok=True)
    (reports / f"training-{args.dataset}-{args.split}.json").write_bytes(canonical_json(report))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
