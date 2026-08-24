"""
external_benchmark.py — Validates MuleNet's EXISTING trained models against
a real-world-derived public AML benchmark (the IBM AML dataset), without
retraining or touching any production .pkl files.

This is a read-only validation/reporting script: it builds an nx.DiGraph from
a subsample of the IBM AML CSV, feeds it into the SAME MuleNetDetectionAgent
pipeline used by /api/v1/detect in production, and reports precision/recall/
F1/false-positive-rate against the dataset's real money-laundering labels.

HOW TO GET THE DATA (Kaggle requires a login, so this isn't automated):
  1. https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
  2. Download "HI-Small_Trans.csv" — the smallest split (still ~5M rows,
     which is why this script subsamples rather than loading it all).
  3. Place it anywhere, e.g. ml_service/data/HI-Small_Trans.csv

USAGE:
  python external_benchmark.py --csv data/HI-Small_Trans.csv --n-rows 20000
  python external_benchmark.py --csv data/HI-Small_Trans.csv --n-rows 20000 --out results.json

WHY THIS DATASET: IBM AML's synthetic transactions are explicitly labeled by
laundering typology (fan-out, fan-in, gather-scatter, scatter-gather, cycle,
stack, bipartite) — the same structural patterns MuleNet's synthetic training
generator (_generate_training_data in ml_models.py) is designed to mimic.
Running the trained models against this INDEPENDENT dataset (not the same
synthetic generator used for training) is a genuine external validation,
not just another held-out sample from the same distribution.
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx

sys.path.insert(0, str(Path(__file__).parent))

from agent_loop import MuleNetDetectionAgent  # noqa: E402  (after sys.path fix)


def load_ibm_aml_sample(
    csv_path: str, n_rows: int, seed: int = 42
) -> Tuple[nx.DiGraph, Dict[str, int]]:
    """
    Reservoir-samples n_rows transactions from the IBM AML CSV and builds a
    MuleNet-compatible transaction graph plus node-level ground-truth labels.

    Two gotchas this handles deliberately:
    1. The IBM AML header has TWO columns both literally named "Account"
       (sender account, receiver account). csv.DictReader would silently
       collapse these into one key and lose the sender or receiver — so this
       reads the header positionally instead.
    2. Repeat transactions between the same account pair must accumulate
       into one edge's cumulative "amount", not overwrite it — MuleNet's
       compute_demo_features() reads a single amount per (src, dst) edge, so
       silently overwriting on repeat transactions would understate real
       transaction volume for frequently-transacting pairs.
    """
    random.seed(seed)
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Download HI-Small_Trans.csv from "
            "kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml "
            "and pass its path via --csv."
        )

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

        account_cols = [i for i, col in enumerate(header) if col.strip() == "Account"]
        if len(account_cols) != 2:
            raise ValueError(
                f"Expected exactly 2 columns named 'Account' in the IBM AML header, "
                f"found {len(account_cols)}: {header}. This script expects the "
                f"standard HI-Small_Trans.csv schema — confirm you downloaded the "
                f"right file from the Kaggle page linked at the top of this script."
            )
        from_idx, to_idx = account_cols
        try:
            amount_idx = header.index("Amount Paid")
            label_idx = header.index("Is Laundering")
        except ValueError as e:
            raise ValueError(
                f"Unexpected IBM AML schema, missing expected column: {e}. "
                f"Header found was: {header}"
            )

        # Reservoir sampling: avoids loading a multi-million-row file into memory.
        reservoir: List[list] = []
        for i, row in enumerate(reader):
            if len(reservoir) < n_rows:
                reservoir.append(row)
            else:
                j = random.randint(0, i)
                if j < n_rows:
                    reservoir[j] = row

    graph = nx.DiGraph()
    labels: Dict[str, int] = {}
    skipped = 0

    for row in reservoir:
        try:
            src = f"ACC_{row[from_idx].strip()}"
            dst = f"ACC_{row[to_idx].strip()}"
            amount = float(row[amount_idx])
            is_laundering = int(row[label_idx])
        except (ValueError, IndexError):
            skipped += 1
            continue  # skip malformed rows rather than crash the whole run

        graph.add_node(src, node_type="account")
        graph.add_node(dst, node_type="account")

        if graph.has_edge(src, dst):
            graph[src][dst]["amount"] += amount
            graph[src][dst]["tx_count"] = graph[src][dst].get("tx_count", 1) + 1
        else:
            graph.add_edge(src, dst, amount=amount, edge_type="sent_to", tx_count=1)

        # Node-level label = laundering-linked if involved in ANY flagged
        # transaction. Aggregating edge-level labels to node-level this way
        # matches the approach used in published IBM-AML graph-learning papers.
        labels[src] = max(labels.get(src, 0), is_laundering)
        labels[dst] = max(labels.get(dst, 0), is_laundering)

    if skipped:
        print(f"Skipped {skipped} malformed rows out of {len(reservoir)} sampled.")

    return graph, labels


def run_benchmark(
    csv_path: str, n_rows: int = 20000, threshold: float = 0.80, seed: int = 42
) -> Dict:
    print(f"Loading up to {n_rows} transactions from {csv_path} (seed={seed})...")
    graph, labels = load_ibm_aml_sample(csv_path, n_rows=n_rows, seed=seed)

    n_mule_accounts = sum(1 for v in labels.values() if v == 1)
    print(f"Graph built: {graph.number_of_nodes()} accounts, {graph.number_of_edges()} unique transacting pairs")
    print(
        f"Ground-truth laundering-linked accounts: {n_mule_accounts} "
        f"({n_mule_accounts / max(len(labels), 1) * 100:.2f}%)"
    )

    print(f"Running MuleNetDetectionAgent (threshold={threshold}) — same pipeline as /api/v1/detect...")
    agent = MuleNetDetectionAgent(threshold=threshold)
    report = agent.run_pipeline(graph, ground_truth=labels)
    cost = report["false_positive_cost_analysis"]

    print("\n=== External Validation: IBM AML Dataset (independent of MuleNet's training data) ===")
    print(f"Precision:           {cost['precision']:.4f}")
    print(f"Recall:              {cost['recall']:.4f}")
    print(f"F1:                  {cost['f1']:.4f}")
    print(f"False Positive Rate: {cost['false_positive_rate']:.4f}")
    print(f"Confusion matrix:    {cost['confusion_matrix']}")

    return {
        "source": "IBM AML (HI-Small) — public AML benchmark, independent of MuleNet's synthetic training data",
        "n_transactions_sampled": n_rows,
        "n_accounts": graph.number_of_nodes(),
        "n_mule_labeled_accounts": n_mule_accounts,
        "threshold": threshold,
        "metrics": cost,
        "run_id": report["run_id"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark MuleNet's existing trained models against the IBM AML public dataset."
    )
    parser.add_argument("--csv", required=True, help="Path to HI-Small_Trans.csv (downloaded from Kaggle)")
    parser.add_argument("--n-rows", type=int, default=20000, help="Number of transactions to sample (default 20000)")
    parser.add_argument("--threshold", type=float, default=0.80, help="Flagging threshold (default 0.80)")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed for reproducibility")
    parser.add_argument("--out", default=None, help="Optional path to save results as JSON")
    args = parser.parse_args()

    result = run_benchmark(args.csv, n_rows=args.n_rows, threshold=args.threshold, seed=args.seed)

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to {args.out}")
