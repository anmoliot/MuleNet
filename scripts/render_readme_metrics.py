"""Render measured README values from report JSON; --check never changes files."""

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def number(value):
    if value is None:
        return "not estimable"
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError("Report contains a nonfinite or nonnumeric measurement")
    return f"{value:.4f}"


def estimate(model, key):
    point = model["metrics"][key]
    value, interval = point["value"], point["ci95"]
    method = "bootstrap"
    exact = model.get("exact_binomial_ci95", {}).get(key)
    if interval and interval[0] == interval[1] and exact:
        interval, method = exact, "exact binomial"
    if value is None:
        return {"value": None, "ci95": None, "interval_method": method}
    number(value)
    if interval is None or len(interval) != 2:
        raise ValueError("A measured value must carry its uncertainty interval")
    for bound in interval:
        number(bound)
    if not interval[0] <= value <= interval[1]:
        raise ValueError("Point estimate lies outside its reported interval")
    return {"value": value, "ci95": interval, "interval_method": method}


def cell(measurement):
    if measurement["value"] is None:
        return "not estimable"
    low, high = measurement["ci95"]
    suffix = " exact" if measurement["interval_method"] == "exact binomial" else ""
    return f"{number(measurement['value'])} [{number(low)}, {number(high)}]{suffix}"


def build(reports):
    inputs = {}

    def read(name):
        report = json.loads((reports / name).read_bytes())
        inputs[name] = hashlib.sha256(canonical(report)).hexdigest()
        return report

    rows = []
    for split in ("temporal", "entity"):
        report = read(f"metrics-sim-{split}.json")
        model_name = report["metadata"]["operating_model"]
        model = report["models"][model_name]
        rows.append(
            {
                "dataset": "Local simulator",
                "split": split,
                "model": model_name,
                "threshold": model["threshold"],
                "test_rows": model["n"],
                "operating_point": report["metadata"]["operating_point"],
                "pr_auc": estimate(model, "pr_auc"),
                "recall": estimate(model, "recall"),
                "fpr": estimate(model, "fpr"),
            }
        )
    paysim = read("metrics-paysim-temporal.json")["models"]["pre_transfer"]
    rows.append(
        {
            "dataset": "PaySim (pre-transfer)",
            "split": "temporal",
            "model": "XGBoost",
            "threshold": paysim["threshold"],
            "test_rows": paysim["n"],
            "operating_point": "VAL only; empirical FPR bound in training protocol",
            "pr_auc": estimate(paysim, "pr_auc"),
            "recall": estimate(paysim, "recall"),
            "fpr": estimate(paysim, "fpr"),
        }
    )
    latency = read("latency.json")
    if latency["mode"] != "model":
        raise ValueError("README latency block currently supports explicitly model-only measurements")
    table = [
        "All datasets below are simulated. Values include 95% confidence intervals.",
        "",
        "| Dataset | Split | Model | Test rows | VAL threshold | PR-AUC | Recall | FPR |",
        "|---|---|---|---:|---:|---|---|---|",
    ]
    for row in rows:
        table.append(
            f"| {row['dataset']} | {row['split']} | {row['model']} | {row['test_rows']} | {number(row['threshold'])} | {cell(row['pr_auc'])} | {cell(row['recall'])} | {cell(row['fpr'])} |"
        )
    table.extend(
        [
            "",
            f"Simulator operating point: {rows[0]['operating_point']}.",
            "The displayed threshold is rounded; serving uses the full-precision artifact value.",
        ]
    )
    speed = [
        "Model-only, single-request wall-clock timings in milliseconds.",
        "",
        "| Load | Requests | Concurrency | p50 | p95 | p99 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for load in ("steady", "burst"):
        record = latency[load]
        speed.append(
            f"| {load} | {record['requests']} | {record['concurrency']} | {number(record['p50_ms'])} | {number(record['p95_ms'])} | {number(record['p99_ms'])} |"
        )
    pipeline = read("latency-pipeline.json") if (reports / "latency-pipeline.json").exists() else None
    architecture = [
        "| Boundary | Steady p50 / p95 / p99 (ms) | Burst p50 / p95 / p99 (ms) | Target budget |",
        "|---|---|---|---|",
    ]
    model_cells = [" / ".join(number(latency[load][f"p{p}_ms"]) for p in (50, 95, 99)) for load in ("steady", "burst")]
    architecture.append(f"| Graph-tabular model-only | {model_cells[0]} | {model_cells[1]} | Not set |")
    if pipeline and pipeline.get("status") == "measured":
        speed.extend(
            [
                "",
                "Actual-network local stack; individual request timings with 95% bootstrap intervals (ms).",
                "",
                "| Boundary | Load | Requests | Concurrency | p50 | p95 | p99 |",
                "|---|---|---:|---:|---|---|---|",
            ]
        )
        for surface, label in (("http", "ML HTTP"), ("kafka_to_sse", "Kafka producer-to-SSE")):
            cells = []
            for load in ("steady", "burst"):
                record = pipeline[surface][load]
                values = [
                    cell(dict(record["quantiles"][f"p{p}_ms"], interval_method="bootstrap")) for p in (50, 95, 99)
                ]
                speed.append(
                    f"| {label} | {load} | {record['requests']} | {record['concurrency']} | {' | '.join(values)} |"
                )
                cells.append(" / ".join(values))
            architecture.append(f"| {label} | {cells[0]} | {cells[1]} | Not set |")
        speed.extend(
            [
                "",
                "Synthetic hot-account traffic on one local stack, not a production SLO. The neural path was not selected or measured.",
                "Kafka timing starts before producer send and ends after receipt of both committed decisions over HTTP SSE; ingestion REST/outbox is excluded.",
                "See [raw network benchmark](reports/latency-pipeline.json) for identities, sample timings, precise boundaries and limitations.",
            ]
        )
    else:
        speed.extend(
            ["", "End-to-end: **not measured successfully**. See [model-only evidence](reports/latency.json)."]
        )
    for stage in (
        "Kafka queue alone",
        "Feature fetch alone",
        "GNN path",
        "Policy/persistence alone",
        "SSE delivery alone",
    ):
        architecture.append(f"| {stage} | Not measured | Not measured | Not set |")
    return {
        "data_provenance": "synthetic",
        "rows": rows,
        "latency": latency,
        "pipeline": pipeline,
        "source_canonical_json_sha256": inputs,
    }, {
        "METRICS": "\n".join(table),
        "LATENCY": "\n".join(speed),
        "ARCH_LATENCY": "\n".join(architecture),
    }


def replace_block(document, name, content):
    start, end = f"<!-- {name}:START -->", f"<!-- {name}:END -->"
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f"Require exactly one {name} marker pair")
    prefix, tail = document.split(start)
    _, suffix = tail.split(end)
    return f"{prefix}{start}\n{content}\n{end}{suffix}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    receipt, blocks = build(ROOT / "reports")
    path, receipt_path = ROOT / "README.md", ROOT / "reports/readme-metrics.json"
    original = path.read_text(encoding="utf-8")
    rendered = original
    for name in ("METRICS", "LATENCY"):
        rendered = replace_block(rendered, name, blocks[name])
    architecture_path = ROOT / "docs/ARCHITECTURE.md"
    architecture = architecture_path.read_text(encoding="utf-8")
    updated_architecture = replace_block(architecture, "ARCH_LATENCY", blocks["ARCH_LATENCY"])
    if args.check:
        if (
            original != rendered
            or architecture != updated_architecture
            or not receipt_path.exists()
            or json.loads(receipt_path.read_bytes()) != receipt
        ):
            raise SystemExit("Generated README evidence is stale or was edited; rerun the renderer")
    else:
        path.write_text(rendered, encoding="utf-8", newline="\n")
        architecture_path.write_text(updated_architecture, encoding="utf-8", newline="\n")
        receipt_path.write_bytes(canonical(receipt))
    print(
        "PASS: README tables match measured JSON reports"
        if args.check
        else "Rendered README tables and reports/readme-metrics.json"
    )


if __name__ == "__main__":
    main()
