"""Tie-aware rank/calibration metrics with stratified bootstrap intervals."""

import numpy as np
from scipy.stats import beta


def _calculate(values, positives, negatives, threshold, top_k, days, fp_cost, fn_cost, calibrated):
    total_positive, total_negative = positives.sum(), negatives.sum()
    total = total_positive + total_negative
    pos, neg, descending = positives[::-1], negatives[::-1], values[::-1]
    tp_curve, fp_curve = np.cumsum(pos), np.cumsum(neg)
    tpr = tp_curve / total_positive if total_positive else np.zeros_like(tp_curve)
    fpr = fp_curve / total_negative if total_negative else np.zeros_like(fp_curve)
    precision_curve = tp_curve / np.maximum(tp_curve + fp_curve, 1)
    flagged = values >= threshold
    tp, fp = positives[flagged].sum(), negatives[flagged].sum()
    fn, tn = total_positive - tp, total_negative - fp
    counts = pos + neg
    k = min(top_k, total)
    fractions = np.clip(k - np.r_[0, np.cumsum(counts)[:-1]], 0, counts) / np.maximum(counts, 1)
    result = {
        "roc_auc": float(np.trapezoid(np.r_[0, tpr], np.r_[0, fpr])) if total_positive and total_negative else None,
        "pr_auc": float(np.sum(np.diff(np.r_[0, tpr]) * precision_curve)) if total_positive else None,
        "recall_at_fpr_0_001": float(np.max(np.r_[0, tpr[fpr <= .001]])) if total_positive and total_negative else None,
        "recall_at_fpr_0_01": float(np.max(np.r_[0, tpr[fpr <= .01]])) if total_positive and total_negative else None,
        "precision_top_k": float(min(np.sum(fractions * pos), k) / k) if k else None,
        "precision": float(tp / (tp + fp)) if tp + fp else None,
        "recall": float(tp / total_positive) if total_positive else None,
        "fpr": float(fp / total_negative) if total_negative else None,
        "alerts_per_day": float((tp + fp) / days),
        "assumed_false_freeze_cost_inr": float(fp * fp_cost),
        "assumed_missed_case_cost_inr": float(fn * fn_cost),
        "tp": float(tp), "fp": float(fp), "fn": float(fn), "tn": float(tn),
    }
    if calibrated:
        bins = np.minimum((values * 10).astype(int), 9)
        bin_counts = np.bincount(bins, weights=positives + negatives, minlength=10)
        bin_positive = np.bincount(bins, weights=positives, minlength=10)
        bin_score = np.bincount(bins, weights=values * (positives + negatives), minlength=10)
        result["ece"] = float(np.sum(np.abs(bin_positive - bin_score)) / total)
        result["brier"] = float(np.sum(positives * (1 - values)**2 + negatives * values**2) / total)
    return result


def summarize(y, scores, threshold, *, resamples=1000, seed=42, top_k=50, days=1, fp_cost=1000, fn_cost=50000, calibrated=True):
    y, scores = np.asarray(y), np.asarray(scores, dtype=float)
    if len(y) != len(scores) or len(y) == 0 or not set(np.unique(y)) <= {0, 1} or not np.isfinite(scores).all():
        raise ValueError("Metrics require aligned, nonempty binary truth and finite scores")
    y = y.astype(int)
    if resamples < 1000 or days <= 0 or top_k < 1 or fp_cost < 0 or fn_cost < 0:
        raise ValueError("Require >=1000 bootstrap resamples and valid exposure/cost parameters")
    if calibrated and ((scores < 0).any() or (scores > 1).any()):
        raise ValueError("Calibrated probabilities must be in [0,1]")
    values, inverse = np.unique(scores, return_inverse=True)
    positive = np.bincount(inverse, weights=(y == 1), minlength=len(values))
    negative = np.bincount(inverse, weights=(y == 0), minlength=len(values))
    operating_threshold = float("inf") if threshold is None else threshold
    point = _calculate(values, positive, negative, operating_threshold, top_k, days, fp_cost, fn_cost, calibrated)
    if not calibrated:
        point = {name: value for name, value in point.items() if name in {"roc_auc", "pr_auc", "recall_at_fpr_0_001", "recall_at_fpr_0_01", "precision_top_k"}}
    rng = np.random.default_rng(seed)
    draws = {name: [] for name in point}
    # Multinomial score-bin counts exactly implement a stratified row bootstrap,
    # including ties, without allocating a full large-dataset copy per resample.
    for _ in range(resamples):
        pos = rng.multinomial(int(positive.sum()), positive / positive.sum()) if positive.sum() else positive
        neg = rng.multinomial(int(negative.sum()), negative / negative.sum()) if negative.sum() else negative
        sample = _calculate(values, pos, neg, operating_threshold, top_k, days, fp_cost, fn_cost, calibrated)
        for name, value in sample.items():
            if name in draws and value is not None:
                draws[name].append(value)
    exact = {}
    if calibrated:
        for name, success, trials in (("fpr", point["fp"], point["fp"] + point["tn"]),
                                      ("recall", point["tp"], point["tp"] + point["fn"]),
                                      ("precision", point["tp"], point["tp"] + point["fp"])):
            exact[name] = None if trials == 0 else [0.0 if success == 0 else float(beta.ppf(.025, success, trials - success + 1)),
                                                     1.0 if success == trials else float(beta.ppf(.975, success + 1, trials - success))]
    return {
        "metrics": {name: {"value": value, "ci95": [float(v) for v in np.quantile(draws[name], [.025, .975])] if draws[name] and value is not None else None} for name, value in point.items()},
        "n": len(y), "positives": int(y.sum()), "threshold": float(threshold) if threshold is not None else None,
        "bootstrap": {"resamples": resamples, "seed": seed, "method": "stratified row bootstrap via exact score-bin multinomials", "limitation": "row bootstrap does not model account/ring dependence"},
        "top_k": top_k, "top_k_ties": "fractional tie-average", "exposure_days": days,
        "cost_assumptions": {"false_freeze_inr": fp_cost, "missed_case_inr": fn_cost, "measured_economic_benefit": False},
        "undefined_precision": "null when no alerts; never manufactured zero or one",
        "exact_binomial_ci95": exact,
        "exact_interval_note": "Additional i.i.d. Clopper-Pearson bounds expose uncertainty when empirical bootstrap degenerates at zero events; account dependence remains a limitation",
    }


def recall_interval(hits, *, seed=42, resamples=1000):
    hits = np.asarray(hits, dtype=float)
    if len(hits) == 0:
        return {"value": None, "ci95": None, "n": 0}
    rng = np.random.default_rng(seed)
    values, counts = np.unique(hits, return_counts=True)
    draws = (rng.multinomial(len(hits), counts / len(hits), size=resamples) @ values) / len(hits)
    return {"value": float(hits.mean()), "ci95": [float(v) for v in np.quantile(draws, [.025, .975])], "n": len(hits)}
