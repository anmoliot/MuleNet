"""MuleNet detection agent for detect -> explain -> cost -> alert -> audit."""

from datetime import datetime
from typing import Any, Dict, List, Optional

import networkx as nx
import numpy as np

from config import AVG_RAZORPAY_PAYOUT_INR, FP_OPPORTUNITY_COST_RATE, MODEL_WEIGHTS
from graph_analytics import detect_fraud_rings, find_connected_fraud_components
from ml_models import (
    FEATURE_COLS,
    calibrate_score,
    get_anomaly_detector,
    get_fast_path,
    get_gnn_scorer,
    get_model_metadata,
)
from shap_explainer import generate_risk_attribution_report


class MuleNetDetectionAgent:
    """Runs the merchant payout risk demo with audit-grade intermediate outputs."""

    def __init__(self, threshold: float = 0.80):
        self.threshold = threshold
        self.fast_path = get_fast_path()
        self.gnn = get_gnn_scorer()
        self.anomaly = get_anomaly_detector()
        self.run_id = f"mulenet-{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}"
        self.audit_log: List[Dict[str, str]] = []

    def run_pipeline(self, graph: nx.DiGraph, ground_truth: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        self._log("PIPELINE_START", f"Started run on {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges.")

        features = compute_demo_features(graph)
        self._log("FEATURE_COMPUTE", f"Computed account features for {len(features)} accounts.")

        scores = self._detect(features, graph)
        flagged_count = sum(1 for score in scores.values() if score["flagged"])
        self._log("DETECTION", f"Flagged {flagged_count} accounts at threshold {self.threshold:.2f}.")

        explanations = self._explain(features, scores)
        self._log("EXPLANATION", f"Generated explanations for {len(explanations)} flagged accounts.")

        cost_analysis = self._compute_fp_cost(scores, ground_truth)
        self._log("COST_ANALYSIS", f"False-positive cost INR {cost_analysis['false_positive_cost_inr']:.2f}.")

        failures = self.handle_cold_starts(features)
        self._log("FAILURE_HANDLING", f"Handled {len(failures)} cold-start accounts with monitor-only policy.")

        clusters = self._detect_clusters(graph, scores)
        self._log("CLUSTER_DETECTION", f"Identified {len(clusters)} suspected mule clusters.")

        report = self._build_report(graph, scores, explanations, cost_analysis, failures, clusters, ground_truth)
        self._log("REPORT_BUILD", f"Completed audit report {self.run_id}.")
        report["audit_log"] = self.audit_log
        return report

    def _detect(self, features: Dict[str, Dict[str, float]], graph: nx.DiGraph) -> Dict[str, Dict[str, Any]]:
        fast_scores = self.fast_path.predict(features)
        model_graph = nx.relabel_nodes(
            graph,
            {node: f"account:{node}" for node in features if graph.has_node(node)},
            copy=True,
        )
        gnn_scores = self.gnn.predict(model_graph, features)
        anomaly_scores = self.anomaly.predict(features)
        topology = topology_scores(graph, features)
        scores: Dict[str, Dict[str, Any]] = {}

        for account_id in features:
            pattern_score = behavioral_pattern_score(features[account_id])
            raw_score = (
                fast_scores.get(account_id, 0.0) * 100 * MODEL_WEIGHTS["fast_path"]
                + gnn_scores.get(account_id, 0.0) * 100 * MODEL_WEIGHTS["gnn"]
                + anomaly_scores.get(account_id, 0.0) * 100 * MODEL_WEIGHTS["anomaly"]
                + topology.get(account_id, 0.0) * MODEL_WEIGHTS["topology"]
                + pattern_score
            )
            composite = calibrate_score(raw_score)
            risk_level = _risk_level(composite)
            scores[account_id] = {
                "account_id": account_id,
                "composite_score": composite,
                "fast_path_score": round(fast_scores.get(account_id, 0.0), 4),
                "gnn_score": round(gnn_scores.get(account_id, 0.0), 4),
                "anomaly_score": round(anomaly_scores.get(account_id, 0.0), 4),
                "topology_score": round(topology.get(account_id, 0.0), 2),
                "behavioral_pattern_score": round(pattern_score, 2),
                "risk_level": risk_level,
                "confidence": "HIGH" if composite >= 75 else "MEDIUM" if composite >= 50 else "LOW",
                "flagged": composite >= self.threshold * 100,
                "action": _action_for_score(composite),
            }
        return dict(sorted(scores.items(), key=lambda item: item[1]["composite_score"], reverse=True))

    def _explain(self, features: Dict[str, Dict[str, float]], scores: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        explanations = {}
        for account_id, score in scores.items():
            if not score["flagged"]:
                continue
            try:
                explanations[account_id] = generate_risk_attribution_report(
                    account_id=account_id,
                    features=features[account_id],
                    risk_score=score["composite_score"],
                    risk_level=score["risk_level"],
                    fraud_probability=score["composite_score"] / 100,
                    confidence=0.85 if score["confidence"] == "HIGH" else 0.62,
                    reason_codes=_reason_codes(score, features[account_id]),
                )
            except Exception as exc:
                explanations[account_id] = {
                    "account_id": account_id,
                    "error": "explanation_failed",
                    "message": str(exc),
                    "top_5_risk_drivers": _reason_codes(score, features[account_id]),
                }
        return explanations

    def _compute_fp_cost(self, scores: Dict[str, Dict[str, Any]], ground_truth: Optional[Dict[str, int]]) -> Dict[str, Any]:
        flagged = {account_id for account_id, score in scores.items() if score["flagged"]}
        predicted_negative = set(scores) - flagged

        if ground_truth:
            positives = {account_id for account_id, label in ground_truth.items() if label == 1 and account_id in scores}
            negatives = {account_id for account_id, label in ground_truth.items() if label == 0 and account_id in scores}
            tp = len(flagged & positives)
            fp = len(flagged & negatives)
            fn = len(predicted_negative & positives)
            tn = len(predicted_negative & negatives)
        else:
            tp = 0
            fp = max(0, round(len(flagged) * 0.05))
            fn = 0
            tn = max(len(scores) - len(flagged) - fp, 0)

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)
        fpr = fp / max(fp + tn, 1)
        fp_unit_cost = AVG_RAZORPAY_PAYOUT_INR * FP_OPPORTUNITY_COST_RATE

        return {
            "has_ground_truth": bool(ground_truth),
            "threshold": self.threshold,
            "total_flagged": len(flagged),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
            "false_positive_cost_inr": round(fp * fp_unit_cost, 2),
            "cost_per_false_positive_inr": round(fp_unit_cost, 2),
            "avg_payout_assumption_inr": AVG_RAZORPAY_PAYOUT_INR,
            "opportunity_cost_rate": FP_OPPORTUNITY_COST_RATE,
            "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        }

    def handle_cold_starts(self, features: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        failures = []
        for account_id, feature in features.items():
            if feature.get("out_degree", 0) == 0 and feature.get("in_degree", 0) == 0:
                fallback_score = float(feature.get("device_risk", 0.35))
                failures.append({
                    "account_id": account_id,
                    "issue": "COLD_START_NO_TRANSACTIONS",
                    "fallback_method": "device_fingerprint_scoring",
                    "fallback_score": round(fallback_score, 4),
                    "confidence": "LOW",
                    "action": "MONITOR_ONLY",
                    "required_human_review": True,
                    "explanation": "No automated freeze: graph and transaction features are unavailable.",
                })
        return failures

    def _detect_clusters(self, graph: nx.DiGraph, scores: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        high_risk = [account_id for account_id, score in scores.items() if score["flagged"] and score["composite_score"] >= 70]
        components = find_connected_fraud_components(graph, high_risk)
        rings = detect_fraud_rings(graph)
        clusters = []

        for idx, component in enumerate(components[:8], start=1):
            members = component["all_accounts"]
            member_scores = [scores[member]["composite_score"] for member in members if member in scores]
            if len(member_scores) < 2:
                continue
            clusters.append({
                "cluster_id": f"CLUSTER-{idx:02d}",
                "accounts": members,
                "size": len(members),
                "avg_risk_score": round(float(np.mean(member_scores)), 2),
                "max_risk_score": round(max(member_scores), 2),
                "total_flow": component["total_flow"],
                "cluster_type": "suspected_mule_ring",
            })

        for ring in rings[:4]:
            clusters.append({
                "cluster_id": ring["ring_id"],
                "accounts": ring["members"],
                "size": ring["length"],
                "avg_risk_score": round(float(np.mean([scores[a]["composite_score"] for a in ring["members"] if a in scores] or [0])), 2),
                "max_risk_score": round(max([scores[a]["composite_score"] for a in ring["members"] if a in scores] or [0]), 2),
                "total_flow": ring["cycle_flow"],
                "cluster_type": ring["risk_category"],
            })

        return clusters

    def _build_report(self, graph, scores, explanations, cost_analysis, failures, clusters, ground_truth):
        scored = list(scores.values())
        score_values = [item["composite_score"] for item in scored]
        return {
            "run_id": self.run_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "MuleNet-v2.1-demo",
            "model_metadata": get_model_metadata(),
            "config": {"threshold": self.threshold, "models_used": list(MODEL_WEIGHTS.keys())},
            "graph_summary": {
                "total_nodes": graph.number_of_nodes(),
                "total_edges": graph.number_of_edges(),
                "merchants": sum(1 for _, data in graph.nodes(data=True) if data.get("node_type") == "merchant"),
                "beneficiaries": sum(1 for _, data in graph.nodes(data=True) if data.get("node_type") == "beneficiary"),
            },
            "detection_summary": {
                "total_accounts_scored": len(scores),
                "flagged_accounts": sum(1 for item in scored if item["flagged"]),
                "critical_count": sum(1 for item in scored if item["risk_level"] == "CRITICAL"),
                "high_count": sum(1 for item in scored if item["risk_level"] == "HIGH"),
                "medium_count": sum(1 for item in scored if item["risk_level"] == "MEDIUM"),
                "low_count": sum(1 for item in scored if item["risk_level"] == "LOW"),
                "clusters_detected": len(clusters),
                "average_score": round(float(np.mean(score_values)), 2) if score_values else 0.0,
            },
            "scores": scores,
            "score_distribution": score_distribution(score_values),
            "explanations": explanations,
            "clusters": clusters,
            "false_positive_cost_analysis": cost_analysis,
            "graceful_failures": failures,
            "ground_truth_available": bool(ground_truth),
            "status": "success",
        }

    def _log(self, event: str, description: str) -> None:
        self.audit_log.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "description": description,
        })


def compute_demo_features(graph: nx.DiGraph, cold_start_accounts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Dict[str, float]]:
    """Compute the eight model features expected by existing MuleNet models."""
    features: Dict[str, Dict[str, float]] = {}
    account_nodes = [
        node for node, data in graph.nodes(data=True)
        if data.get("node_type") in {"merchant", "beneficiary", "account"} or node.startswith(("ACC_", "MERCH_", "CASHOUT_"))
    ]
    total_flow = sum(data.get("amount", 0.0) for _, _, data in graph.edges(data=True) if data.get("edge_type") == "sent_to") or 1.0

    for node in account_nodes:
        outgoing = [graph[node][target].get("amount", 0.0) for target in graph.successors(node) if graph[node][target].get("edge_type") == "sent_to"]
        incoming = [graph[source][node].get("amount", 0.0) for source in graph.predecessors(node) if graph[source][node].get("edge_type") == "sent_to"]
        total_sent = sum(outgoing)
        total_recv = sum(incoming)
        flow_base = max(total_sent, total_recv, 1e-9)
        probabilities = [amount / max(total_sent, 1e-9) for amount in outgoing] if outgoing else []
        entropy = -sum(p * np.log(p + 1e-9) for p in probabilities)

        features[node] = {
            "out_degree": len(outgoing),
            "in_degree": len(incoming),
            "total_sent": round(total_sent, 2),
            "total_recv": round(total_recv, 2),
            "pass_through_rate": round(min(total_sent, total_recv) / flow_base, 4),
            "fan_out_ratio": round(len(outgoing) / max(len(incoming), 1), 4),
            "counterparty_entropy": round(float(entropy), 4),
            "share_of_total_flow": round(total_sent / total_flow, 4),
        }

    for account in cold_start_accounts or []:
        features[account["account_id"]] = {
            **{column: 0.0 for column in FEATURE_COLS},
            "device_risk": account.get("device_risk", 0.35),
        }

    return features


def topology_scores(graph: nx.DiGraph, features: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    try:
        pagerank = nx.pagerank(graph, weight=None, max_iter=100)
    except Exception:
        pagerank = {node: 0.0 for node in graph.nodes}
    try:
        betweenness = nx.betweenness_centrality(graph)
    except Exception:
        betweenness = {node: 0.0 for node in graph.nodes}

    scores = {}
    for account_id, feature in features.items():
        scores[account_id] = min(
            100.0,
            pagerank.get(account_id, 0.0) * 900
            + betweenness.get(account_id, 0.0) * 220
            + feature.get("out_degree", 0) * 4
            + feature.get("pass_through_rate", 0.0) * 22,
        )
    return {account_id: round(score, 2) for account_id, score in scores.items()}


def behavioral_pattern_score(feature: Dict[str, float]) -> float:
    """Rule-shaped mule signal used as a bounded model feature in the demo ensemble."""
    total_recv = feature.get("total_recv", 0.0)
    total_sent = feature.get("total_sent", 0.0)
    pass_through = feature.get("pass_through_rate", 0.0)
    fan_out = feature.get("fan_out_ratio", 0.0)
    degree = feature.get("in_degree", 0) + feature.get("out_degree", 0)
    entropy = feature.get("counterparty_entropy", 0.0)

    return min(
        35.0,
        min(total_recv / 200000.0, 1.0) * 9.0
        + min(total_sent / 90000.0, 1.0) * 9.0
        + min(pass_through / 0.45, 1.0) * 8.0
        + min(fan_out / 2.5, 1.0) * 4.0
        + min(degree / 6.0, 1.0) * 3.0
        + min(entropy / 1.2, 1.0) * 2.0,
    )


def score_distribution(scores: List[float]) -> Dict[str, int]:
    return {
        "critical": sum(1 for score in scores if score >= 90),
        "high": sum(1 for score in scores if 75 <= score < 90),
        "medium": sum(1 for score in scores if 60 <= score < 75),
        "low": sum(1 for score in scores if 40 <= score < 60),
        "minimal": sum(1 for score in scores if score < 40),
    }


def _risk_level(score: float) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 75:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "MINIMAL"


def _action_for_score(score: float) -> str:
    if score >= 90:
        return "FREEZE_IMMEDIATE"
    if score >= 75:
        return "SOFT_HOLD"
    if score >= 60:
        return "STEP_UP_MONITOR"
    if score >= 40:
        return "MONITOR"
    return "ALLOW"


def _reason_codes(score: Dict[str, Any], feature: Dict[str, float]) -> List[str]:
    codes = []
    if score["fast_path_score"] >= 0.70:
        codes.append("FAST_PATH_HIGH_RISK")
    if score["gnn_score"] >= 0.70:
        codes.append("GNN_STRUCTURAL_ANOMALY")
    if score["anomaly_score"] >= 0.70:
        codes.append("ISOLATION_FOREST_OUTLIER")
    if feature.get("pass_through_rate", 0.0) >= 0.65:
        codes.append("HIGH_PASS_THROUGH")
    if feature.get("fan_out_ratio", 0.0) >= 2:
        codes.append("FAN_OUT_LAYERING")
    return codes or ["LOW_MODEL_SIGNAL"]
