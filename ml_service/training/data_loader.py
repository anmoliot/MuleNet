import os
import pandas as pd
from typing import Tuple


def load_real_data() -> Tuple[pd.DataFrame, pd.Series]:
    """Load real transaction data from CSV.

    The path is read from the ``REAL_DATA_PATH`` environment variable.
    The CSV must contain a ``label`` column (1 for fraud, 0 for legit).
    All other columns are treated as features.
    """
    path = os.getenv("REAL_DATA_PATH")
    if not path:
        raise FileNotFoundError("REAL_DATA_PATH environment variable not set.")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Real data file not found at {path}")
    df = pd.read_csv(path)
    if "label" not in df.columns:
        raise ValueError("CSV must contain a 'label' column.")
    y = df["label"]
    X = df.drop(columns=["label"])
    return X, y
