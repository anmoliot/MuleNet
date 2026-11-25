"""Reproducible preparation and training for temporal/entity experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import skops.io as sio
import torch

from mulenet_core.artifacts import write_manifest
from mulenet_core.io import canonical_json, read_dataset, load_amlworld, load_paysim
from mulenet_core.labels import materialize
from mulenet_core.schema import Dataset, FeatureConfig, feature_names
from mulenet_core.splits import temporal_split, entity_split, entity_partitions, partition_events
from training.train_gnn import export_gnn, predict_graphs, snapshot_graph, train_gnn
from training.train_tabular import fit_calibrator, select_threshold, train_anomaly, train_stack, train_xgb


def load_input(dataset, path, allow_synthetic=False):
    if dataset == "sim":
        return read_dataset(path, allow_synthetic=allow_synthetic)
    events = load_amlworld(path) if dataset == "amlworld" else load_paysim(path)
    return Dataset(source=dataset, transactions=events)


def prepare(dataset: Dataset, split_name: str, config: FeatureConfig, horizon=21600, seed=42):
    start, end = min(e.ts for e in dataset.transactions), max(e.ts for e in dataset.transactions)
    nodes = sorted({e.source for e in dataset.transactions} | {e.target for e in dataset.transactions})
    first = {node: min(e.ts for e in dataset.transactions if node in (e.source, e.target)) for node in nodes}
    times = range(start + 86400 + 7200, end - horizon, 86400)
    points = [(node, ts) for ts in times for node in nodes if first[node] <= ts]
    if split_name == "temporal":
        rows = materialize(dataset.transactions, points, horizon, end, config, dataset.accounts)
        split = temporal_split(rows, int(start + (end - start) * .6), int(start + (end - start) * .8))
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
        graphs[name] = {ts: snapshot_graph(context[name], rows, config, dataset.accounts) for ts, rows in groups.items()}
    return split, graphs


def train_experiment(dataset, dataset_name, split_name, directory, config, seed=42, epochs=30):
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError("Train into a new immutable version directory")
    directory.mkdir(parents=True, exist_ok=True)
    split, graphs = prepare(dataset, split_name, config, seed=seed)
    names = feature_names(config)
    matrices = {part: np.asarray([[row.features[name] for name in names] for row in getattr(split, part)]) for part in ("train", "val")}
    labels = {part: np.asarray([row.label for row in getattr(split, part)]) for part in ("train", "val")}
    topology = ("flow_hop", "cycle_count", "clustering", "pagerank")
    tabular_indices = [i for i, name in enumerate(names) if not any(term in name for term in topology)]
    tabular = train_xgb(matrices["train"][:, tabular_indices], labels["train"], matrices["val"][:, tabular_indices], labels["val"], seed)
    graph_tabular = train_xgb(matrices["train"], labels["train"], matrices["val"], labels["val"], seed)
    anomaly = train_anomaly(matrices["train"], seed)
    gnn, gnn_training = train_gnn(graphs["train"], graphs["val"], len(names), seed, epochs)
    val_gnn = predict_graphs(gnn, graphs["val"])
    gnn_prob = np.asarray([val_gnn[(row.account_id, row.as_of)] for row in split.val])
    raw = {"tabular": tabular.predict_proba(matrices["val"][:, tabular_indices])[:, 1],
           "tabular_graph": graph_tabular.predict_proba(matrices["val"])[:, 1], "gnn": gnn_prob}
    meta_components = np.column_stack([raw["tabular_graph"], raw["gnn"], -anomaly.score_samples(matrices["val"])])
    stack, fusion_calibration, fusion_oof = train_stack(meta_components, labels["val"], seed)
    calibrators = {name: fit_calibrator(scores, labels["val"]) for name, scores in raw.items()}
    thresholds = {name: select_threshold(labels["val"], calibrators[name].predict(scores)) for name, scores in raw.items()}
    calibrators["fusion"] = fusion_calibration
    thresholds["fusion"] = select_threshold(labels["val"], fusion_oof)
    # The default deep path is decided on VAL only; the test cannot change it.
    recalls = {name: float(np.mean((calibrators[name].predict(raw[name]) >= thresholds[name])[labels["val"] == 1])) for name in ("tabular_graph", "gnn")}
    default_deep = "gnn" if recalls["gnn"] > recalls["tabular_graph"] else "tabular_graph"
    training = {"dataset": dataset_name, "data_provenance": dataset.data_provenance,
                "split": split_name, "seed": seed, "threshold_selection": "VAL only; maximize recall at empirical FPR <= 0.001",
                "thresholds": thresholds, "tabular_indices": tabular_indices, "default_deep_path": default_deep,
                "gnn": gnn_training, "rows": {part: len(getattr(split, part)) for part in ("train", "val", "test")},
                "stacking": "Base models fit on TRAIN; stratified out-of-fold meta predictions on VAL; isotonic on VAL OOF",
                "limitations": ["Synthetic data cannot establish bank effectiveness", "Small VAL has coarse FPR resolution", "Validation calibration and threshold reuse can overfit; TEST remains untouched during fitting"]}
    tabular.save_model(directory / "tabular.ubj")
    graph_tabular.save_model(directory / "tabular_graph.ubj")
    sio.dump(calibrators, directory / "calibration.skops")
    sio.dump(anomaly, directory / "anomaly.skops")
    sio.dump(stack, directory / "stack.skops")
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
    args = parser.parse_args()
    dataset = load_input(args.dataset, args.data, args.allow_synthetic)
    report = train_experiment(dataset, args.dataset, args.split, args.out, FeatureConfig(currency=args.currency), epochs=args.epochs)
    reports = Path(__file__).resolve().parents[2] / "reports"
    reports.mkdir(exist_ok=True)
    (reports / f"training-{args.dataset}-{args.split}.json").write_bytes(canonical_json(report))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
