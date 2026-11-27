"""Measure individual synchronous requests; never divide a batch duration by rows."""

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_service"))


def measure(call, requests, concurrency):
    def sample(_):
        start = time.perf_counter_ns()
        call()
        return (time.perf_counter_ns() - start) / 1_000_000

    for _ in range(10):
        call()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        durations = list(pool.map(sample, range(requests)))
    elapsed = time.perf_counter() - started
    return {
        "requests": len(durations),
        "concurrency": concurrency,
        "p50_ms": float(np.percentile(durations, 50)),
        "p95_ms": float(np.percentile(durations, 95)),
        "p99_ms": float(np.percentile(durations, 99)),
        "elapsed_seconds": elapsed,
        "completed_per_second": requests / elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["model", "http", "pipeline"], required=True)
    parser.add_argument("--wsl", action="store_true")
    parser.add_argument("--models", type=Path)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--url")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.mode == "pipeline":
        from bench_pipeline import run_pipeline

        run_pipeline(
            allow_synthetic=args.allow_synthetic,
            wsl=args.wsl,
            output=args.out or ROOT / "reports/latency-pipeline.json",
        )
        return
    args.out = args.out or ROOT / "reports/latency.json"
    if args.requests < 100:
        parser.error("At least 100 individual requests are required")
    if args.mode == "model":
        if not args.models:
            parser.error("--models is required")
        from mulenet_core.calibration import calibrated_probabilities
        from mulenet_core.features import extract_features
        from mulenet_core.io import read_dataset
        from mulenet_core.models import ModelBundle

        bundle = ModelBundle(args.models, allow_synthetic=args.allow_synthetic)
        fixture = read_dataset(ROOT / "data/generated/training-demo.json", allow_synthetic=args.allow_synthetic)
        row = extract_features(
            fixture.transactions,
            fixture.accounts[0].account_id,
            max(e.ts for e in fixture.transactions),
            bundle.config,
            {a.account_id: a for a in fixture.accounts},
        )
        matrix = bundle.matrix([row])

        def call():
            raw = bundle.graph_tabular.predict_proba(matrix)[:, 1]
            calibrated_probabilities(bundle.calibration["tabular_graph"], raw)

        identity = {
            "model_version": bundle.manifest["model_version"],
            "model": "tabular_graph",
            "excludes": ["feature extraction", "Redis", "HTTP", "Kafka", "policy", "SSE"],
        }
    else:
        import os

        token = os.environ.get("MULENET_BENCH_TOKEN")
        if not args.url or not args.payload or not token:
            parser.error("HTTP mode requires --url, --payload and MULENET_BENCH_TOKEN")
        payload = args.payload.read_bytes()
        client = httpx.Client(
            timeout=10, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

        def call():
            client.post(args.url, content=payload).raise_for_status()

        identity = {
            "url": args.url,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "excludes": ["Kafka", "backend policy", "SSE"],
        }
    report = {
        "mode": args.mode,
        "data_provenance": "synthetic",
        "identity": identity,
        "steady": measure(call, args.requests, 1),
        "burst": measure(call, args.requests, 8),
        "end_to_end": {
            "status": "not_measured",
            "reason": "Requires Kafka-to-SSE correlation harness; model/HTTP timings are not end-to-end latency",
        },
    }
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
