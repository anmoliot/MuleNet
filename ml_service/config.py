"""Central configuration for the MuleNet merchant-risk demo API."""

import os
ALLOWED_ORIGINS = ["*"]

DEFAULT_THRESHOLD = float(os.getenv("MULENET_DEMO_THRESHOLD", "0.80"))
DEFAULT_TEST_ACCOUNTS = int(os.getenv("MULENET_DEMO_TEST_ACCOUNTS", "50"))
DEFAULT_MULE_RATIO = float(os.getenv("MULENET_DEMO_MULE_RATIO", "0.15"))
DEFAULT_SEED = int(os.getenv("MULENET_DEMO_SEED", "42"))

AVG_RAZORPAY_PAYOUT_INR = float(os.getenv("MULENET_AVG_PAYOUT_INR", "12500"))
FP_OPPORTUNITY_COST_RATE = float(os.getenv("MULENET_FP_COST_RATE", "0.03"))

MODEL_WEIGHTS = {
    "fast_path": 0.40,
    "gnn": 0.30,
    "anomaly": 0.20,
    "topology": 0.10,
}
