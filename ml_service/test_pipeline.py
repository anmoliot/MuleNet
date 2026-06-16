"""Quick end-to-end pipeline test."""
from graph_builder import IntakeRequest, Complaint, Transaction, build_hetero_graph, real_inference
import json

req = IntakeRequest(
    complaint=Complaint(complaint_id="COMP-101", utr="UTR-98472910", amount=100000.0, timestamp="2023-10-01T12:00:00", first_beneficiary="AC-7739"),
    transactions=[
        Transaction(utr="UTR-98472910", amount=100000.0, timestamp="2023-10-01T12:00:00", sender_account="AC-VICTIM", receiver_account="AC-7739", device_id="DEV-111"),
        Transaction(utr="UTR-11111111", amount=25000.0, timestamp="2023-10-01T12:01:00", sender_account="AC-7739", receiver_account="AC-8102", device_id="DEV-111"),
        Transaction(utr="UTR-22222222", amount=25000.0, timestamp="2023-10-01T12:01:10", sender_account="AC-7739", receiver_account="AC-3994", device_id="DEV-222"),
        Transaction(utr="UTR-33333333", amount=50000.0, timestamp="2023-10-01T12:01:20", sender_account="AC-7739", receiver_account="AC-1199", device_id="DEV-111"),
        Transaction(utr="UTR-44444444", amount=25000.0, timestamp="2023-10-01T12:05:00", sender_account="AC-8102", receiver_account="AC-1199", device_id="DEV-333"),
        Transaction(utr="UTR-55555555", amount=25000.0, timestamp="2023-10-01T12:05:10", sender_account="AC-3994", receiver_account="AC-1199", device_id="DEV-444"),
    ]
)
G = build_hetero_graph(req)
result = real_inference(G, req)
print("STATUS:", result["status"])
print("MODEL VERSION:", result["model_version"])
print("RECOVERY RANKING:")
for r in result["recovery_ranking"]:
    acct = r["account_id"]
    print(f"  {acct}: composite={r['composite_score']}, XGB={r['fast_path_score']:.3f}, GNN={r['gnn_score']:.3f}, action={r['action_recommendation']}")
print("TIMINGS:", json.dumps(result["timings"], indent=2))
print("RECOVERY SUMMARY:", json.dumps(result.get("recovery_summary", {}), indent=2))
print("FREEZE ORDERING:")
for f in result.get("freeze_ordering", []):
    print(f"  P{f['freeze_priority']}: {f['account_id']} balance={f['estimated_balance']} recovery={f['recovery_potential']} urgency={f['urgency']}")
