"""
external_intel.py — External Intelligence Layer (Stub)
Simulates I4C, NCRP, Suspect Registry, and Watchlist lookups.
Returns enrichment data that feeds into the scoring pipeline.
"""

import hashlib
import random
from typing import Dict, List, Optional
from pydantic import BaseModel


class WatchlistHit(BaseModel):
    source: str
    match_type: str  # EXACT, FUZZY, DEVICE_LINKED
    confidence: float
    alert_id: Optional[str] = None
    details: str


class ExternalEnrichment(BaseModel):
    account_id: str
    watchlist_hits: List[WatchlistHit]
    risk_uplift: float  # Additional risk score from external intel
    i4c_status: Optional[str] = None
    ncrp_complaints: int = 0
    known_mule: bool = False


# ── Stub Watchlists ──────────────────────────────────────────────────────────
# Deterministic "hits" seeded by account ID hash so results are reproducible

_SUSPECT_REGISTRY = {
    "AC-1199": {"source": "I4C_SUSPECT_REGISTRY", "alert": "I4C-2024-88291"},
    "AC-8102": {"source": "NCRP_FLAGGED", "alert": "NCRP-2024-44102"},
}

_DEVICE_BLACKLIST = {"DEV-111", "DEV-333"}


def _hash_score(value: str) -> float:
    """Deterministic pseudo-random score from a string."""
    h = int(hashlib.sha256(value.encode()).hexdigest()[:8], 16)
    return (h % 100) / 100.0


def check_watchlists(account_id: str, device_ids: List[str] = None) -> ExternalEnrichment:
    """
    Query external intelligence sources for an account.
    Currently stub — returns deterministic mock data.
    In production, this would call I4C API, NCRP database, etc.
    """
    hits: List[WatchlistHit] = []
    risk_uplift = 0.0
    known_mule = False
    ncrp_complaints = 0

    # Check suspect registry
    if account_id in _SUSPECT_REGISTRY:
        entry = _SUSPECT_REGISTRY[account_id]
        hits.append(WatchlistHit(
            source=entry["source"],
            match_type="EXACT",
            confidence=0.95,
            alert_id=entry["alert"],
            details=f"Account {account_id} found in {entry['source']}"
        ))
        risk_uplift += 25.0
        known_mule = True
        ncrp_complaints = int(_hash_score(account_id) * 5) + 1

    # Check device blacklist
    if device_ids:
        for dev in device_ids:
            if dev in _DEVICE_BLACKLIST:
                hits.append(WatchlistHit(
                    source="DEVICE_BLACKLIST",
                    match_type="DEVICE_LINKED",
                    confidence=0.80,
                    details=f"Device {dev} linked to {account_id} is on blacklist"
                ))
                risk_uplift += 10.0

    # Fuzzy watchlist check (deterministic based on account hash)
    acct_hash = _hash_score(account_id)
    if acct_hash > 0.7 and account_id not in _SUSPECT_REGISTRY:
        hits.append(WatchlistHit(
            source="FUZZY_WATCHLIST",
            match_type="FUZZY",
            confidence=round(0.4 + acct_hash * 0.3, 2),
            details=f"Partial name/PAN match for {account_id} in regional watchlist"
        ))
        risk_uplift += 5.0

    # I4C status
    i4c_status = "FLAGGED" if known_mule else "CLEAR"

    return ExternalEnrichment(
        account_id=account_id,
        watchlist_hits=hits,
        risk_uplift=min(risk_uplift, 40.0),
        i4c_status=i4c_status,
        ncrp_complaints=ncrp_complaints,
        known_mule=known_mule,
    )


def batch_check(
    account_ids: List[str],
    device_map: Dict[str, List[str]] = None,
) -> Dict[str, ExternalEnrichment]:
    """
    Batch query all accounts against external intelligence.
    Returns dict keyed by account_id.
    """
    results = {}
    device_map = device_map or {}
    for acct in account_ids:
        devices = device_map.get(acct, [])
        results[acct] = check_watchlists(acct, devices)
    return results
