"""
external_intel.py — External Intelligence Layer
Queries Spring Boot /api/external/watchlist endpoint.
Returns database-driven enrichment data that feeds into the scoring pipeline.
"""

import requests
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


def check_watchlists(account_id: str, device_ids: List[str] = None) -> ExternalEnrichment:
    """
    Query external watchlist API. Wrapper for legacy single checks.
    """
    dev_map = {account_id: device_ids or []}
    res = batch_check([account_id], dev_map)
    return res[account_id]


def batch_check(
    account_ids: List[str],
    device_map: Dict[str, List[str]] = None,
) -> Dict[str, ExternalEnrichment]:
    """
    Batch query all accounts and device IDs against Spring Boot external intelligence registry.
    """
    device_map = device_map or {}
    all_devices = []
    for dev_list in device_map.values():
        all_devices.extend(dev_list)

    payload = {
        "accountIds": account_ids,
        "deviceIds": list(set(all_devices))
    }

    # Initialize baseline clean results
    results = {}
    for acct in account_ids:
        results[acct] = ExternalEnrichment(
            account_id=acct,
            watchlist_hits=[],
            risk_uplift=0.0,
            i4c_status="CLEAR",
            ncrp_complaints=0,
            known_mule=False
        )

    try:
        # Call Spring Boot database lookups
        res = requests.post("http://localhost:8080/api/external/watchlist", json=payload, timeout=5)
        if res.status_code == 200:
            hits = res.json()
            for hit in hits:
                item_id = hit.get("accountId")
                source = hit.get("source")
                risk_uplift = hit.get("riskUplift", 0.0)
                match_type = hit.get("matchType", "EXACT")
                confidence = hit.get("confidence", 1.0)
                details = hit.get("details", "")

                watchlist_hit = WatchlistHit(
                    source=source,
                    match_type=match_type,
                    confidence=confidence,
                    details=details
                )

                # Check if this hit is for one of our query accounts
                if item_id in results:
                    results[item_id].watchlist_hits.append(watchlist_hit)
                    results[item_id].risk_uplift = min(results[item_id].risk_uplift + risk_uplift, 40.0)
                    if source in ["I4C_SUSPECT_REGISTRY", "NCRP_FLAGGED", "CONSORTIUM_BLACKLIST"]:
                        results[item_id].known_mule = True
                        results[item_id].i4c_status = "FLAGGED"
                        if source == "NCRP_FLAGGED":
                            results[item_id].ncrp_complaints = 3  # simulated count

                # Or if this hit is for a device associated with our query accounts
                for acct, devices in device_map.items():
                    if item_id in devices and acct in results:
                        # Append a device-linked hit details
                        results[acct].watchlist_hits.append(WatchlistHit(
                            source=source,
                            match_type="DEVICE_LINKED",
                            confidence=confidence * 0.9,
                            details=f"Device {item_id} linked: {details}"
                        ))
                        results[acct].risk_uplift = min(results[acct].risk_uplift + risk_uplift * 0.8, 40.0)
                        results[acct].i4c_status = "FLAGGED" if results[acct].known_mule else "SUSPICIOUS"

        else:
            print(f"[Watchlist] External check failed with status: {res.status_code}")
    except Exception as e:
        print(f"[Watchlist] Exception during database threat intel search: {str(e)}")

    return results
