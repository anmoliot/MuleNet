"""Validate probabilities; bound only floating-point representation error."""

import numpy as np

PROBABILITY_TOLERANCE = 4 * np.finfo(np.float32).eps


def calibrated_probabilities(calibrator, scores, diagnostics=None):
    values = np.asarray(calibrator.predict(np.asarray(scores)), dtype=np.float64)
    if not np.isfinite(values).all() or np.any(values < -PROBABILITY_TOLERANCE) or np.any(values > 1 + PROBABILITY_TOLERANCE):
        raise ValueError("Calibrator emitted invalid probabilities beyond floating-point tolerance")
    bounded = np.clip(values, 0, 1)
    if diagnostics is not None:
        diagnostics.update({"bounded_values": int(np.count_nonzero(values != bounded)),
                            "maximum_overshoot": float(max(0, values.max(initial=0) - 1, -values.min(initial=0))),
                            "tolerance": float(PROBABILITY_TOLERANCE)})
    return bounded
