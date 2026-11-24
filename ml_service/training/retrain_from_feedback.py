"""Quarantine adjudications before retraining; case outcomes are not transaction labels."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import time


def eligible_feedback(rows, *, now, cooling_seconds=604800, max_per_reviewer=20):
    groups = defaultdict(list)
    counts = defaultdict(int)
    for row in rows:
        counts[row["reviewer"]] += 1
        groups[row["decision_id"]].append(row)
    accepted, rejected = [], []
    for decision_id, reviews in sorted(groups.items()):
        reasons = []
        if len({r["reviewer"] for r in reviews}) < 2:
            reasons.append("independent_second_review_required")
        if len({r["fraudulent"] for r in reviews}) != 1 or any(type(r["fraudulent"]) is not bool for r in reviews):
            reasons.append("disagreement_or_invalid_label")
        if not any(r["reviewer_role"] in {"SUPERVISOR", "ADMIN"} for r in reviews):
            reasons.append("supervisor_adjudication_required")
        if any(r["created_at"] > now - cooling_seconds or r["as_of"] >= r["created_at"] for r in reviews):
            reasons.append("cooling_period_or_label_clock_invalid")
        if any(counts[r["reviewer"]] > max_per_reviewer for r in reviews):
            reasons.append("reviewer_concentration_requires_manual_review")
        if reasons:
            rejected.append({"decision_id": decision_id, "reasons": reasons})
        else:
            accepted.append({"decision_id": decision_id, "account_id": reviews[0]["account_id"], "as_of": reviews[0]["as_of"], "fraudulent": reviews[0]["fraudulent"], "reviewers": sorted({r["reviewer"] for r in reviews})})
    return {"eligible_adjudications": accepted, "quarantined": rejected,
            "automatic_promotion": False, "transaction_label_conversion": False,
            "next_gate": "Link independently verified transaction evidence, preserve unknown negatives, protect validation/test cohorts, cap feedback mixture and compare a shadow candidate before manual promotion"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feedback", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--as-of", type=int, default=None)
    args = parser.parse_args()
    report = eligible_feedback(json.loads(args.feedback.read_bytes()), now=int(time.time()) if args.as_of is None else args.as_of)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("Adjudications quarantined/quality-checked; no labels inferred from case status and no model automatically trained or promoted")


if __name__ == "__main__":
    main()
