"""Run actual-network Testcontainers latency measurements with uncertainty."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def summarize_load(load, *, resamples=1000, seed=42):
    values = np.asarray(load["durations_ms"], dtype=np.float64)
    if values.ndim != 1 or len(values) < 100 or len(values) != load["requests"]:
        raise ValueError("Require at least 100 individual, aligned request measurements")
    if not np.isfinite(values).all() or np.any(values <= 0) or load["degraded_decisions"] != 0:
        raise ValueError("Reject nonfinite timings, failed requests or degraded-path benchmarks")
    if resamples < 1000 or load["concurrency"] < 1 or load["elapsed_seconds"] <= 0:
        raise ValueError("Invalid load exposure or bootstrap configuration")
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(resamples, len(values)), replace=True)
    quantiles = {}
    for percentile in (50, 95, 99):
        distribution = np.percentile(draws, percentile, axis=1)
        quantiles[f"p{percentile}_ms"] = {
            "value": float(np.percentile(values, percentile)),
            "ci95": [float(v) for v in np.percentile(distribution, [2.5, 97.5])],
        }
    return dict(
        load,
        quantiles=quantiles,
        completed_per_second=len(values) / load["elapsed_seconds"],
        bootstrap={
            "resamples": resamples,
            "seed": seed,
            "method": "IID request bootstrap",
            "limitation": "Requests share a host, account and service state; intervals do not model deployment or temporal dependence",
        },
    )


def run_pipeline(*, allow_synthetic, wsl, output):
    if not allow_synthetic:
        raise ValueError("Pipeline benchmark requires explicit --allow-synthetic")
    raw = ROOT / ".tools/pipeline-latency-raw.json"
    raw.unlink(missing_ok=True)
    command = [
        sys.executable,
        str(ROOT / "scripts/record_maven_tests.py"),
        "--tests",
        "PlatformLatencyTest,ReviewPolicyTest",
        "--out",
        str(ROOT / "reports/pipeline-bench-tests.json"),
    ]
    if wsl:
        command.append("--wsl")
    execution = subprocess.run(command, cwd=ROOT, check=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    if execution.returncode or not raw.exists():
        output.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "metrics": None,
                    "reason": "Real-network benchmark did not pass; old measurements are not reused",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise RuntimeError(
            "Pipeline benchmark failed; inspect reports/pipeline-bench-tests.json and .tools/platform-test.log"
        )
    measurement = json.loads(raw.read_bytes())
    if measurement["data_provenance"] != "synthetic" or measurement["model"] != "tabular_graph":
        raise ValueError("Unexpected benchmark provenance or model path")
    for surface in ("http", "kafka_to_sse"):
        measurement[surface] = {load: summarize_load(measurement[surface][load]) for load in ("steady", "burst")}
    report = dict(
        measurement,
        status="measured",
        raw_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        test_receipt_sha256=hashlib.sha256((ROOT / "reports/pipeline-bench-tests.json").read_bytes()).hexdigest(),
        latency_clock="Client process monotonic clock, individual requests; no batch-duration division",
        production_approved=False,
        gnn_path="not measured: not the selected candidate path",
        limitations=[
            "Closed-loop fixed concurrency; worker queue wait is outside request timing; no open-loop capacity claim",
            "Synthetic hot-account workload; a single-node local stack, not production capacity",
            "Warmups omitted from quantiles; initial service startup excluded",
            "Kafka starts before producer send, not after broker acknowledgment",
            "SSE includes network serialization and receipt of both account decisions",
            "Failed/degraded runs fail the benchmark rather than being dropped from percentiles",
        ],
    )
    output.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                surface: {load: measurement[surface][load]["quantiles"] for load in ("steady", "burst")}
                for surface in ("http", "kafka_to_sse")
            },
            sort_keys=True,
        )
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--wsl", action="store_true")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/latency-pipeline.json")
    args = parser.parse_args()
    try:
        run_pipeline(allow_synthetic=args.allow_synthetic, wsl=args.wsl, output=args.out)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Benchmark refused: {exc}\n")


if __name__ == "__main__":
    main()
