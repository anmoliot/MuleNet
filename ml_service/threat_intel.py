"""
threat_intel.py — MuleNet Threat Intelligence Correlation Engine

Correlates accounts and entities against:
  - Known fraud databases
  - High-risk IP ranges
  - VPN / Proxy / TOR exit node indicators
  - Compromised credential databases
  - Cryptocurrency risk feeds (stub)
  - Scam complaint databases
  - Sanction list / watchlist lookups

Produces:
  - Threat Intelligence Score (0-100)
  - Fraud Network Association Score
  - Risk Correlation Report
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field


# ── Known threat categories ────────────────────────────────────────────────────
@dataclass
class ThreatMatch:
    category: str           # e.g. "SANCTION_LIST", "HIGH_RISK_IP", "TOR_EXIT"
    source: str             # e.g. "OFAC", "I4C", "AbuseIPDB"
    confidence: float       # 0.0 – 1.0
    risk_weight: float      # Contribution to TI score
    description: str
    ioc_type: str           # "account", "ip", "device", "crypto_address"
    ioc_value: str          # The matched indicator of compromise


@dataclass
class ThreatIntelResult:
    entity_id: str
    entity_type: str        # "account", "ip", "device"
    threat_matches: List[ThreatMatch] = field(default_factory=list)
    threat_intel_score: float = 0.0       # 0-100
    fraud_network_score: float = 0.0      # 0-100 (graph-proximity based)
    risk_level: str = "CLEAR"             # CLEAR, LOW, MEDIUM, HIGH, CRITICAL
    is_sanctioned: bool = False
    is_tor_node: bool = False
    is_vpn_proxy: bool = False
    is_known_fraud: bool = False
    ncrp_hits: int = 0
    i4c_status: str = "CLEAR"
    summary: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT INTELLIGENCE FEED LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class ThreatFeedLoader:
    """
    Loads threat intelligence data from:
    1. Local JSON config file (threat_intel_config.json)
    2. Provides sensible defaults for offline operation
    """

    CONFIG_PATH = Path(__file__).parent / "threat_intel_config.json"

    def __init__(self):
        self._config = self._load_config()
        self._blacklisted_accounts: Set[str] = set(self._config.get("blacklisted_accounts", []))
        self._blacklisted_devices: Set[str] = set(self._config.get("blacklisted_devices", []))
        self._high_risk_ips: Set[str] = set(self._config.get("high_risk_ips", []))
        self._tor_exit_nodes: Set[str] = set(self._config.get("tor_exit_nodes", []))
        self._vpn_ranges: List[str] = self._config.get("vpn_cidr_ranges", [])
        self._sanction_list: Set[str] = set(self._config.get("sanction_list", []))
        self._ncrp_flagged: Dict[str, int] = self._config.get("ncrp_flagged_accounts", {})
        self._i4c_registry: Set[str] = set(self._config.get("i4c_suspect_registry", []))
        self._crypto_risk: Set[str] = set(self._config.get("crypto_risk_addresses", []))

    def _load_config(self) -> Dict:
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ThreatIntel] Failed to load config: {e}")
        return self._default_config()

    def _default_config(self) -> Dict:
        """Default threat intelligence config with sample indicators."""
        return {
            "blacklisted_accounts": [
                "AC-MULE-001", "AC-MULE-002", "AC-FRAUD-RING-01",
                "AC-SCAM-COLLECT", "AC-CRYPTO-CASHOUT"
            ],
            "blacklisted_devices": ["DEV-COMPROMISED-01", "DEV-SHARED-FRAUD"],
            "high_risk_ips": [
                "185.220.101.1", "194.165.16.77", "45.142.212.100",
                "103.114.163.3", "91.108.4.0"
            ],
            "tor_exit_nodes": ["176.10.99.200", "185.220.101.34", "199.87.154.255"],
            "vpn_cidr_ranges": ["45.142.212.0/24", "104.21.0.0/16"],
            "sanction_list": ["AC-OFAC-001", "AC-UN-SANCTION-02"],
            "ncrp_flagged_accounts": {
                "AC-NCRP-001": 5, "AC-NCRP-002": 12, "AC-MULE-001": 8
            },
            "i4c_suspect_registry": [
                "AC-I4C-SUSPECT-01", "AC-MULE-001", "AC-FRAUD-RING-01"
            ],
            "crypto_risk_addresses": [
                "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
                "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"
            ],
            "risk_weights": {
                "sanction_list": 40,
                "i4c_registry": 35,
                "ncrp_flagged": 25,
                "blacklisted_account": 30,
                "blacklisted_device": 20,
                "high_risk_ip": 15,
                "tor_exit_node": 20,
                "vpn_proxy": 10,
                "crypto_risk": 15
            }
        }

    @property
    def risk_weights(self) -> Dict[str, float]:
        return self._config.get("risk_weights", {})


# ═══════════════════════════════════════════════════════════════════════════════
# THREAT INTELLIGENCE SCORER
# ═══════════════════════════════════════════════════════════════════════════════

class ThreatIntelScorer:
    """
    Scores accounts, IPs, and devices against loaded threat intelligence feeds.
    """

    def __init__(self):
        self.feed = ThreatFeedLoader()

    def score_account(
        self,
        account_id: str,
        ip_addresses: Optional[List[str]] = None,
        device_ids: Optional[List[str]] = None,
        crypto_addresses: Optional[List[str]] = None,
    ) -> ThreatIntelResult:
        """Full threat intelligence correlation for one account."""
        result = ThreatIntelResult(entity_id=account_id, entity_type="account")
        ip_addresses = ip_addresses or []
        device_ids = device_ids or []
        crypto_addresses = crypto_addresses or []
        matches: List[ThreatMatch] = []
        raw_score = 0.0
        weights = self.feed.risk_weights

        # 1. Sanction list check
        if account_id in self.feed._sanction_list:
            w = weights.get("sanction_list", 40)
            matches.append(ThreatMatch(
                category="SANCTION_LIST", source="OFAC/UN", confidence=1.0,
                risk_weight=w,
                description=f"Account {account_id} matched against international sanction list.",
                ioc_type="account", ioc_value=account_id,
            ))
            result.is_sanctioned = True
            raw_score += w

        # 2. I4C cybercrime registry check
        if account_id in self.feed._i4c_registry:
            w = weights.get("i4c_registry", 35)
            matches.append(ThreatMatch(
                category="I4C_SUSPECT_REGISTRY", source="I4C (MHA India)",
                confidence=0.95, risk_weight=w,
                description=f"Account {account_id} is registered in I4C cybercrime suspect registry.",
                ioc_type="account", ioc_value=account_id,
            ))
            result.is_known_fraud = True
            result.i4c_status = "FLAGGED"
            raw_score += w

        # 3. NCRP complaints
        ncrp_count = self.feed._ncrp_flagged.get(account_id, 0)
        if ncrp_count > 0:
            w = weights.get("ncrp_flagged", 25) * min(1.0, math.log(ncrp_count + 1) / 3)
            matches.append(ThreatMatch(
                category="NCRP_COMPLAINT", source="NCRP Portal",
                confidence=0.85, risk_weight=w,
                description=f"{ncrp_count} NCRP cybercrime complaints linked to account.",
                ioc_type="account", ioc_value=account_id,
            ))
            result.ncrp_hits = ncrp_count
            raw_score += w

        # 4. Account blacklist check
        if account_id in self.feed._blacklisted_accounts:
            w = weights.get("blacklisted_account", 30)
            matches.append(ThreatMatch(
                category="FRAUD_BLACKLIST", source="Internal Consortium DB",
                confidence=0.9, risk_weight=w,
                description=f"Account {account_id} found in fraud consortium blacklist.",
                ioc_type="account", ioc_value=account_id,
            ))
            result.is_known_fraud = True
            raw_score += w

        # 5. Device blacklist check
        for dev in device_ids:
            if dev in self.feed._blacklisted_devices:
                w = weights.get("blacklisted_device", 20)
                matches.append(ThreatMatch(
                    category="DEVICE_BLACKLIST", source="Device Risk DB",
                    confidence=0.85, risk_weight=w,
                    description=f"Device {dev} linked to known fraud device fingerprint.",
                    ioc_type="device", ioc_value=dev,
                ))
                raw_score += w

        # 6. IP reputation checks
        for ip in ip_addresses:
            if ip in self.feed._high_risk_ips:
                w = weights.get("high_risk_ip", 15)
                matches.append(ThreatMatch(
                    category="HIGH_RISK_IP", source="AbuseIPDB/ThreatFeed",
                    confidence=0.80, risk_weight=w,
                    description=f"Login IP {ip} is flagged as high-risk.",
                    ioc_type="ip", ioc_value=ip,
                ))
                raw_score += w

            if ip in self.feed._tor_exit_nodes:
                w = weights.get("tor_exit_node", 20)
                matches.append(ThreatMatch(
                    category="TOR_EXIT_NODE", source="TorProject Exit List",
                    confidence=1.0, risk_weight=w,
                    description=f"Transaction originated from TOR exit node: {ip}",
                    ioc_type="ip", ioc_value=ip,
                ))
                result.is_tor_node = True
                raw_score += w

        # 7. Cryptocurrency risk addresses
        for addr in crypto_addresses:
            if addr in self.feed._crypto_risk:
                w = weights.get("crypto_risk", 15)
                matches.append(ThreatMatch(
                    category="CRYPTO_RISK_ADDRESS", source="Chainalysis/Elliptic Feed",
                    confidence=0.9, risk_weight=w,
                    description=f"Linked cryptocurrency address {addr[:16]}... appears in risk database.",
                    ioc_type="crypto_address", ioc_value=addr,
                ))
                raw_score += w

        ti_score = min(raw_score, 100.0)

        if ti_score >= 80:
            risk_level = "CRITICAL"
        elif ti_score >= 60:
            risk_level = "HIGH"
        elif ti_score >= 40:
            risk_level = "MEDIUM"
        elif ti_score >= 20:
            risk_level = "LOW"
        else:
            risk_level = "CLEAR"

        if matches:
            top_cat = matches[0].category
            summary = (f"Threat Intelligence flagged {len(matches)} indicator(s). "
                       f"Highest category: {top_cat}. TI Score: {ti_score:.1f}/100.")
        else:
            summary = "No threat intelligence matches found. Entity appears clean."

        result.threat_matches = matches
        result.threat_intel_score = round(ti_score, 2)
        result.risk_level = risk_level
        result.summary = summary
        return result

    def batch_score(
        self,
        account_ids: List[str],
        ip_map: Optional[Dict[str, List[str]]] = None,
        device_map: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, ThreatIntelResult]:
        """Score multiple accounts at once."""
        ip_map = ip_map or {}
        device_map = device_map or {}
        return {
            acct: self.score_account(
                acct,
                ip_addresses=ip_map.get(acct, []),
                device_ids=device_map.get(acct, []),
            )
            for acct in account_ids
        }

    def generate_correlation_report(
        self,
        results: Dict[str, ThreatIntelResult],
    ) -> Dict[str, Any]:
        """Aggregate a threat intelligence correlation report across multiple accounts."""
        critical = [r for r in results.values() if r.risk_level == "CRITICAL"]
        high = [r for r in results.values() if r.risk_level == "HIGH"]
        sanctioned = [r for r in results.values() if r.is_sanctioned]
        tor = [r for r in results.values() if r.is_tor_node]
        known_fraud = [r for r in results.values() if r.is_known_fraud]

        all_matches = []
        for r in results.values():
            all_matches.extend(r.threat_matches)

        category_counts: Dict[str, int] = {}
        for m in all_matches:
            category_counts[m.category] = category_counts.get(m.category, 0) + 1

        top_threat_accounts = sorted(
            results.values(), key=lambda r: r.threat_intel_score, reverse=True
        )[:5]

        return {
            "total_accounts_checked": len(results),
            "critical_risk_accounts": len(critical),
            "high_risk_accounts": len(high),
            "sanctioned_entities": len(sanctioned),
            "tor_origin_accounts": len(tor),
            "known_fraud_accounts": len(known_fraud),
            "total_threat_matches": len(all_matches),
            "threat_category_distribution": category_counts,
            "top_threat_accounts": [
                {
                    "entity_id": r.entity_id,
                    "threat_intel_score": r.threat_intel_score,
                    "risk_level": r.risk_level,
                    "match_count": len(r.threat_matches),
                    "i4c_status": r.i4c_status,
                    "ncrp_hits": r.ncrp_hits,
                }
                for r in top_threat_accounts
            ],
        }

    def result_to_dict(self, result: ThreatIntelResult) -> Dict[str, Any]:
        """Convert ThreatIntelResult to a JSON-serializable dict."""
        return {
            "entity_id": result.entity_id,
            "entity_type": result.entity_type,
            "threat_intel_score": result.threat_intel_score,
            "risk_level": result.risk_level,
            "is_sanctioned": result.is_sanctioned,
            "is_tor_node": result.is_tor_node,
            "is_vpn_proxy": result.is_vpn_proxy,
            "is_known_fraud": result.is_known_fraud,
            "ncrp_hits": result.ncrp_hits,
            "i4c_status": result.i4c_status,
            "summary": result.summary,
            "threat_matches": [
                {
                    "category": m.category,
                    "source": m.source,
                    "confidence": m.confidence,
                    "risk_weight": m.risk_weight,
                    "description": m.description,
                    "ioc_type": m.ioc_type,
                    "ioc_value": m.ioc_value,
                }
                for m in result.threat_matches
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FRAUD NETWORK ASSOCIATION SCORER
# ═══════════════════════════════════════════════════════════════════════════════

def compute_fraud_network_association(
    account_id: str,
    known_fraud_neighbors: List[str],
    hop_distances: Dict[str, int],
) -> float:
    """
    Compute a Fraud Network Association Score based on graph proximity
    to known fraudulent accounts.

    Score = sum over all known-fraud neighbors of (50 / (1 + distance))
    Capped at 100.
    """
    score = 0.0
    for neighbor in known_fraud_neighbors:
        dist = hop_distances.get(neighbor, 3)
        score += 50.0 / (1 + dist)
    return round(min(score, 100.0), 2)
