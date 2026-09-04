"""
preprocess.py — MuleNet canonical preprocessing
ONE source of truth for feature construction, used by training
(Kaggle notebook / training scripts) AND serving (/api/stream/next).
Training-serving skew = model scores noise. This file prevents it.
"""

import numpy as np
import pandas as pd

# The 8-feature order used by the live service (ml_models.FEATURE_COLS)
FEATURE_COLS = ["out_degree", "in_degree", "total_sent", "total_recv",
                "pass_through_rate", "fan_out_ratio", "counterparty_entropy",
                "share_of_total_flow"]

MONEY_COLS = [2, 3]          # indices of total_sent, total_recv in the matrix
CLIP_BOUNDS = {0: (0, 50), 1: (0, 50), 4: (0, 1), 5: (0, 10),
               6: (0, 1), 7: (0, 1)}   # per-feature sane ranges


# ═══════════════════════════════════════════════════════════════════════════
# 1. CLEANING (PaySim schema: step,type,nameOrig,oldbalanceOrg,newbalanceOrig,
#    nameDest,oldbalanceDest,newbalanceDest,amount,isFraud,isFlaggedFraud)
# ═══════════════════════════════════════════════════════════════════════════

def clean_paysim(df: pd.DataFrame) -> pd.DataFrame:
    print(f"[CLEAN] raw: {len(df):,} rows")
    # a) exact duplicates
    df = df.drop_duplicates()
    # b) drop the useless rule-based column
    df = df.drop(columns=["isFlaggedFraud"], errors="ignore")
    # c) fraud only occurs in TRANSFER + CASH_OUT — filter early
    df = df[df["type"].isin(["TRANSFER", "CASH_OUT"])].copy()
    # d) missing values: PaySim has none, but guard for other datasets
    df = df.dropna(subset=["nameOrig", "nameDest", "amount", "isFraud"])
    # e) sanity: non-negative amounts
    df = df[df["amount"] >= 0]
    print(f"[CLEAN] after filter/dedup: {len(df):,} rows, "
          f"{int(df['isFraud'].sum()):,} fraud txns")
    return df


# ═══════════════════════════════════════════════════════════════════════════
# 2. AGGREGATION to per-account rows (train-safe: dataset-level stats from
#    TRAIN accounts only → no leakage into the test split)
# ═══════════════════════════════════════════════════════════════════════════

def _entropy(series: pd.Series) -> float:
    vc = series.value_counts()
    p = vc / vc.sum()
    return float(-(p * np.log2(p)).sum())


def build_account_features(df: pd.DataFrame, stats: dict = None):
    """
    df: CLEANED transactions.
    stats: pass on TEST split to reuse TRAIN-only normalization stats.
           None on TRAIN → stats are computed here and returned.
    Returns (X, y, stats).
    """
    def _agg(part: pd.DataFrame, total_flow: float, max_entropy: float):
        fraud_dest = set(part.loc[part["isFraud"] == 1, "nameDest"])
        fraud_orig = set(part.loc[part["isFraud"] == 1, "nameOrig"])
        out = part.groupby("nameOrig").agg(
            out_degree=("amount", "size"), total_sent=("amount", "sum"),
            out_cp=("nameDest", pd.Series.nunique))
        inc = part.groupby("nameDest").agg(
            in_degree=("amount", "size"), total_recv=("amount", "sum"),
            inc_cp=("nameOrig", pd.Series.nunique))
        entropy_map = part.groupby("nameDest")["nameOrig"].apply(_entropy).to_dict()
        accounts = inc.index.union(out.index)

        rows, labels = [], []
        for acct in accounts:
            o = out.loc[acct] if acct in out.index else None
            i = inc.loc[acct] if acct in inc.index else None
            total_sent = float(o["total_sent"]) if o is not None else 0.0
            total_recv = float(i["total_recv"]) if i is not None else 0.0
            out_cp = int(o["out_cp"]) if o is not None else 0
            inc_cp = int(i["inc_cp"]) if i is not None else 0
            rows.append([
                int(o["out_degree"]) if o is not None else 0,
                int(i["in_degree"]) if i is not None else 0,
                total_sent, total_recv,
                min(total_recv / max(total_sent, 1.0), 1.0),      # pass-through
                out_cp / max(inc_cp, 1),                          # fan-out
                min(entropy_map.get(acct, 0.0) / max_entropy, 1.0),
                (total_sent + total_recv) / max(total_flow, 1.0), # share of flow
            ])
            labels.append(1 if (acct in fraud_dest or acct in fraud_orig) else 0)
        return np.array(rows, dtype=np.float64), np.array(labels, dtype=np.int64)

    if stats is None:                                  # TRAIN path
        max_entropy = np.log2(max(df["nameOrig"].nunique(), 2))
        total_flow = float(df["amount"].sum())
        stats = {"max_entropy": max_entropy, "total_flow": total_flow}
        X, y = _agg(df, total_flow, max_entropy)
    else:                                              # TEST path — reuse stats
        X, y = _agg(df, stats["total_flow"], stats["max_entropy"])

    X = to_feature_scale(X)
    return X, y, stats


def to_feature_scale(X: np.ndarray) -> np.ndarray:
    """
    THE canonical per-feature transform — also used at serving time.
    log1p on money, clip to sane ranges. Trees don't need scaling,
    but they DO need the same distribution at train and serve.
    """
    X = X.copy()
    X[:, MONEY_COLS] = np.log1p(X[:, MONEY_COLS])
    for idx, (lo, hi) in CLIP_BOUNDS.items():
        X[:, idx] = np.clip(X[:, idx], lo, hi)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X


# ═══════════════════════════════════════════════════════════════════════════
# 3. SERVING-SIDE builder — identical transform for the live path
# ═══════════════════════════════════════════════════════════════════════════

def build_live_features(rolling_acct_stats: dict, total_flow: float,
                        max_entropy: float) -> dict:
    """
    Build ONE live feature dict from the account's rolling window stats
    (what a real Kafka consumer would maintain), then apply the SAME
    to_feature_scale transforms. rolling_acct_stats example:
      {"out_degree": 4, "in_degree": 3, "total_sent": 185000.0,
       "total_recv": 170000.0, "out_cp": 2, "inc_cp": 3,
       "cp_entropy_raw": 1.2}
    """
    f = {
        "out_degree": float(rolling_acct_stats.get("out_degree", 0)),
        "in_degree": float(rolling_acct_stats.get("in_degree", 0)),
        "total_sent": float(np.log1p(rolling_acct_stats.get("total_sent", 0))),
        "total_recv": float(np.log1p(rolling_acct_stats.get("total_recv", 0))),
        "pass_through_rate": min(
            rolling_acct_stats.get("total_recv", 0) /
            max(rolling_acct_stats.get("total_sent", 1.0), 1.0), 1.0),
        "fan_out_ratio": min(
            rolling_acct_stats.get("out_cp", 0) /
            max(rolling_acct_stats.get("inc_cp", 1), 1), 10.0),
        "counterparty_entropy": min(
            rolling_acct_stats.get("cp_entropy_raw", 0.0) / max_entropy, 1.0),
        "share_of_total_flow": min(
            (rolling_acct_stats.get("total_sent", 0) +
             rolling_acct_stats.get("total_recv", 0)) / max(total_flow, 1.0), 1.0),
    }
    return f   # dict keys = FEATURE_COLS order when passed to models
