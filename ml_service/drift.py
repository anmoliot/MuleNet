"""Distribution monitoring; drift triggers review, never automatic model promotion."""

import numpy as np
from scipy.stats import ks_2samp


def distribution_shift(reference, observed, bins=10):
    reference, observed = np.asarray(reference, dtype=float), np.asarray(observed, dtype=float)
    if len(reference) < 2 or len(observed) < 2 or not np.isfinite(reference).all() or not np.isfinite(observed).all():
        raise ValueError("Drift requires finite reference and observed samples")
    cuts = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(cuts) == 1:
        cuts = np.array([cuts[0], np.nextafter(cuts[0], np.inf)])
    edges = np.concatenate(([-np.inf], cuts, [np.inf]))
    expected = np.histogram(reference, edges)[0].astype(float) + 0.5
    actual = np.histogram(observed, edges)[0].astype(float) + 0.5
    expected, actual = expected / expected.sum(), actual / actual.sum()
    psi = float(np.sum((actual - expected) * np.log(actual / expected)))
    ks = ks_2samp(reference, observed)
    return {
        "psi": psi,
        "ks": float(ks.statistic),
        "ks_pvalue": float(ks.pvalue),
        "review_trigger": bool(psi >= 0.2 or (ks.statistic >= 0.1 and ks.pvalue < 0.01)),
        "action": "review_data_then_shadow_retrain; never_auto_promote",
    }
