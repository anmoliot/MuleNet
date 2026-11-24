"""Causal-in-time future-path measurement, not a bank-recovery estimator."""

import numpy as np


def temporal_path(events, account_id, as_of, terminal_id, end, max_hops=3):
    reachable = {(account_id, 0): as_of}
    for event in sorted(events, key=lambda e: (e.ts, e.transaction_id)):
        if not as_of < event.ts <= end:
            continue
        for (node, hops), arrived in tuple(reachable.items()):
            if node == event.source and arrived <= event.ts and hops < max_hops:
                if event.transaction_id == terminal_id:
                    return {"seconds_before_terminal": event.ts - as_of, "hops_before_terminal": hops + 1}
                key = (event.target, hops + 1)
                reachable[key] = min(reachable.get(key, event.ts), event.ts)
    return None


def terminal_coverage(events, rows, scores, threshold, ledger):
    detected, covered = [], set()
    for row, score in zip(rows, scores):
        if score < threshold or not row.label:
            continue
        candidates = []
        for terminal in ledger:
            if row.as_of < terminal["ts"] <= row.label_end:
                path = temporal_path(events, row.account_id, row.as_of, terminal["transaction_id"], row.label_end)
                if path:
                    covered.add(terminal["transaction_id"])
                    candidates.append(path)
        if candidates:
            detected.append(min(candidates, key=lambda item: item["seconds_before_terminal"]))
    rng = np.random.default_rng(42)
    result = {"n_detected_paths": len(detected), "method": "nondecreasing event-time paths <=3 hops; simulated terminal ledger; not actual cash-out/recovery"}
    for field in ("seconds_before_terminal", "hops_before_terminal"):
        values = np.asarray([item[field] for item in detected], dtype=float)
        if len(values):
            draws = [np.median(rng.choice(values, size=len(values), replace=True)) for _ in range(1000)]
            result[field] = {"value": float(np.median(values)), "ci95": np.quantile(draws, [.025, .975]).tolist()}
        else:
            result[field] = {"value": None, "ci95": None, "reason": "No detected path at the frozen operating point"}
    eligible = {terminal["transaction_id"]: terminal for terminal in ledger if any(row.as_of < terminal["ts"] <= row.label_end for row in rows)}
    values = np.asarray([item["amount"] if key in covered else 0 for key, item in sorted(eligible.items())], dtype=float)
    result["synthetic_exposure_covered_inr"] = {"value": float(values.sum()), "ci95": np.quantile([rng.choice(values, size=len(values), replace=True).sum() for _ in range(1000)], [.025, .975]).tolist() if len(values) else None,
                                                  "not_intercepted_or_recovered": True}
    return result
