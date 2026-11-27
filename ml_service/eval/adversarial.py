"""Fixed-label observational stress tests, not claims of real-world evasion rates."""

from dataclasses import replace

import numpy as np
from mulenet_core.features import extract_features
from training.train_gnn import predict_graphs, snapshot_graph

ATTACKS = ("structuring", "delayed_relay", "amount_splitting", "merchant_hop", "feature_noise")


def perturb(events, attack):
    result = []
    for event in events:
        if attack == "structuring":
            result.append(event.model_copy(update={"amount": min(event.amount, 49999.0)}))
        elif attack == "delayed_relay":
            result.append(event.model_copy(update={"ts": event.ts + 21600}))
        elif attack == "amount_splitting":
            result.extend(
                event.model_copy(update={"transaction_id": event.transaction_id + suffix, "amount": event.amount / 2})
                for suffix in ("-split-a", "-split-b")
            )
        elif attack == "merchant_hop":
            merchant = "stress-merchant:" + event.source
            result.append(
                event.model_copy(update={"transaction_id": event.transaction_id + "-hop-a", "target": merchant})
            )
            result.append(
                event.model_copy(update={"transaction_id": event.transaction_id + "-hop-b", "source": merchant})
            )
        else:
            result.append(event)
    return tuple(result)


def evaluate_attacks(bundle, events, rows, accounts, baseline_scores, model_name="fusion"):
    from collections import defaultdict

    from eval.metrics import recall_interval

    reports = {}
    positives = np.asarray([row.label == 1 for row in rows])
    threshold = bundle.training["thresholds"][model_name]
    clean_hits = np.asarray(baseline_scores) >= threshold
    for attack in ATTACKS:
        changed = perturb(events, attack)
        groups = defaultdict(list)
        rng = np.random.default_rng(42)
        for row in rows:
            features = extract_features(
                changed, row.account_id, row.as_of, bundle.config, {a.account_id: a for a in accounts}
            )
            if attack == "feature_noise":
                features = {
                    key: float(value + rng.normal() * max(abs(value), 1) * 0.05) for key, value in features.items()
                }
            groups[row.as_of].append(replace(row, features=features))
        graphs = {ts: snapshot_graph(changed, group, bundle.config, accounts) for ts, group in groups.items()}
        gnn = predict_graphs(bundle.gnn, graphs)
        updated = [next(r for r in groups[row.as_of] if r.account_id == row.account_id) for row in rows]
        scores = bundle.predict(
            [row.features for row in updated], [gnn[(row.account_id, row.as_of)] for row in updated]
        )[model_name]
        hits = scores >= threshold
        reports[attack] = {
            "recall": recall_interval(hits[positives]),
            "recall_drop": recall_interval(clean_hits[positives].astype(float) - hits[positives].astype(float)),
            "protocol": "historical observation perturbation; original future labels and VAL threshold held fixed",
        }
    return reports
