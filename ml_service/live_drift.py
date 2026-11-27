"""Bounded tenant/model-isolated windows; a drift signal never changes policy."""

import threading
import time
from collections import OrderedDict, deque

import numpy as np
from drift import distribution_shift
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest


class LiveDrift:
    def __init__(self, registry, *, window=256, minimum=64, capacity=16, max_age_seconds=900, clock=time.monotonic):
        if (
            not 2 <= minimum <= window <= 2048
            or not 1 <= capacity <= 256
            or not np.isfinite(max_age_seconds)
            or max_age_seconds <= 0
        ):
            raise ValueError("Invalid bounded drift-window configuration")
        self.window, self.minimum, self.capacity = window, minimum, capacity
        self.max_age_seconds, self.clock = max_age_seconds, clock
        self.lock = threading.Lock()
        self.windows = OrderedDict()
        self.evictions = Counter(
            "mulenet_ml_drift_window_evictions_total", "Explicit bounded-window evictions", registry=registry
        )

    def observe(self, tenant, bundle, features, probability, model):
        reference = bundle.drift_reference
        if model not in reference.scores or set(features) != set(reference.feature_names):
            raise ValueError("Drift observation does not match the verified reference")
        values = np.asarray([features[name] for name in reference.feature_names], dtype=np.float64)
        if not np.isfinite(values).all() or not np.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Drift requires finite features and a valid probability")
        key = (tenant, bundle.manifest["model_version"], bundle.manifest["files"]["drift-reference.json"], model)
        with self.lock:
            if key not in self.windows:
                if len(self.windows) == self.capacity:
                    self.windows.popitem(last=False)
                    self.evictions.inc()
                self.windows[key] = (reference, deque(maxlen=self.window))
            self.windows[key][1].append((values, float(probability), self.clock()))
            self.windows.move_to_end(key)

    def snapshot(self, tenant):
        with self.lock:
            cutoff = self.clock() - self.max_age_seconds
            for _reference, rows in self.windows.values():
                while rows and rows[0][2] <= cutoff:
                    rows.popleft()
            windows = [
                (key, reference, tuple(rows)) for key, (reference, rows) in self.windows.items() if key[0] == tenant
            ]
        result = []
        for key, reference, rows in windows:
            record = {
                "model_version": key[1],
                "reference_sha256": key[2],
                "model": key[3],
                "samples": len(rows),
                "ready": len(rows) >= self.minimum,
                "statistics": None,
                "action": "review_data_then_shadow_retrain; never_auto_promote",
            }
            if record["ready"]:
                observed = np.stack([row[0] for row in rows])
                baseline = np.asarray(reference.features)
                statistics = {
                    name: distribution_shift(baseline[:, i], observed[:, i])
                    for i, name in enumerate(reference.feature_names)
                }
                statistics["score"] = distribution_shift(reference.scores[key[3]], [row[1] for row in rows])
                record["statistics"] = statistics
                record["review_required"] = any(value["review_trigger"] for value in statistics.values())
            result.append(record)
        return result

    def metrics(self, tenant):
        registry = CollectorRegistry()
        labels = ["model_version", "model", "reference_sha256"]
        samples = Gauge("mulenet_ml_drift_samples", "Current bounded observation count", labels, registry=registry)
        ready = Gauge("mulenet_ml_drift_ready", "Enough observations for statistics", labels, registry=registry)
        review = Gauge(
            "mulenet_ml_drift_review_required",
            "Data review required, not an automated action",
            labels,
            registry=registry,
        )
        statistics = {
            name: Gauge(
                f"mulenet_ml_drift_{name}", f"Measured distribution {name}", labels + ["feature"], registry=registry
            )
            for name in ("psi", "ks", "ks_pvalue")
        }
        for record in self.snapshot(tenant):
            identity = [record["model_version"], record["model"], record["reference_sha256"]]
            samples.labels(*identity).set(record["samples"])
            ready.labels(*identity).set(int(record["ready"]))
            if record["ready"]:
                review.labels(*identity).set(int(record["review_required"]))
                for feature, values in record["statistics"].items():
                    for name, metric in statistics.items():
                        metric.labels(*identity, feature).set(values[name])
        return generate_latest(registry)
