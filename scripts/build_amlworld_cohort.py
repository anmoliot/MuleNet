"""Select complete currency-scoped components, without consulting fraud labels."""

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_data import file_hash

sys.path.insert(0, str(ROOT / "ml_service"))
from mulenet_core.graph import canonical_events
from mulenet_core.io import canonical_json, write_dataset
from mulenet_core.schema import Dataset, Transaction


def build(path, output, *, max_nodes=4096, max_component=64, seed=42):
    if not 1 <= max_component <= max_nodes <= 4096:
        raise ValueError("Invalid explicit cohort bounds")
    union = nx.utils.UnionFind()
    usd_rows = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if header != [
            "Timestamp",
            "From Bank",
            "Account",
            "To Bank",
            "Account",
            "Amount Received",
            "Receiving Currency",
            "Amount Paid",
            "Payment Currency",
            "Payment Format",
            "Is Laundering",
        ]:
            raise ValueError("Unexpected supplier CSV columns")
        for row in reader:
            if len(row) != len(header):
                raise ValueError("Malformed source row")
            if row[8] == "US Dollar":
                usd_rows += 1
                union.union(row[1] + ":" + row[2], row[3] + ":" + row[4])
    components = [tuple(sorted(group)) for group in union.to_sets()]
    eligible = [group for group in components if len(group) <= max_component]
    eligible.sort(key=lambda group: hashlib.sha256((str(seed) + "\0" + "\0".join(group)).encode()).digest())
    selected, selected_components = set(), []
    for group in eligible:
        if len(selected) + len(group) <= max_nodes:
            selected.update(group)
            selected_components.append(hashlib.sha256("\0".join(group).encode()).hexdigest())
    if len(selected_components) < 3:
        raise ValueError("No viable whole-component cohort; never replace with sampled edges")
    events = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        next(reader)
        for line, row in enumerate(reader, 2):
            source, target = row[1] + ":" + row[2], row[3] + ":" + row[4]
            if row[8] == "US Dollar" and source in selected and target in selected:
                if row[10] not in {"0", "1"}:
                    raise ValueError("Unknown cohort label")
                events.append(
                    Transaction(
                        transaction_id=f"amlworld:{line}",
                        source=source,
                        target=target,
                        ts=int(datetime.strptime(row[0], "%Y/%m/%d %H:%M").replace(tzinfo=UTC).timestamp()),
                        amount=float(row[7]),
                        currency="USD",
                        kind=row[9],
                        fraud=row[10] == "1",
                    )
                )
    dataset = Dataset(source="amlworld-whole-component-cohort:" + path.stem, transactions=canonical_events(events))
    digest = write_dataset(dataset, output)
    receipt = {
        "source_file": path.name,
        "source_sha256": file_hash(path),
        "cohort_sha256": digest,
        "data_provenance": "synthetic",
        "seed": seed,
        "currency": "USD",
        "selection": "hash-ranked complete weak components; no labels consulted",
        "source_usd_edges": usd_rows,
        "source_components": len(components),
        "eligible_components": len(eligible),
        "excluded_large_component_nodes": sum(len(group) for group in components if len(group) > max_component),
        "selected_components": selected_components,
        "selected_nodes": len(selected),
        "selected_edges": len(events),
        "flagged_edges": sum(event.fraud is True for event in events),
        "max_component_nodes": max_component,
        "limitations": [
            "USD-only small-component cohort, not full AMLworld",
            "Large connected networks explicitly excluded",
            "No cross-currency conversion or inferred typology annotations",
        ],
    }
    output.with_suffix(".receipt.json").write_bytes(canonical_json(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=["HI-Small", "LI-Small"], required=True)
    parser.add_argument("--max-nodes", type=int, default=4096)
    parser.add_argument("--max-component", type=int, default=64)
    args = parser.parse_args()
    path = ROOT / "data/raw/amlworld" / f"{args.variant}_Trans.csv"
    output = ROOT / "data/processed" / f"{args.variant}-cohort.json"
    report = build(path, output, max_nodes=args.max_nodes, max_component=args.max_component)
    (ROOT / "reports" / f"cohort-{args.variant}.json").write_bytes(canonical_json(report))
    print(json.dumps({key: value for key, value in report.items() if key != "selected_components"}, sort_keys=True))


if __name__ == "__main__":
    main()
