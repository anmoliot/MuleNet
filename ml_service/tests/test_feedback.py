import json

from training.retrain_from_feedback import eligible_feedback, main


def test_feedback_requires_independent_cooled_consensus_and_never_infers_edge_labels(tmp_path, monkeypatch):
    row = {"decision_id": "case", "account_id": "account-token", "as_of": 100,
           "created_at": 200, "reviewer": "one", "reviewer_role": "ANALYST", "fraudulent": True}
    assert not eligible_feedback([row], now=1_000_000)["eligible_adjudications"]
    supervisor = dict(row, reviewer="two", reviewer_role="SUPERVISOR")
    assert not eligible_feedback([row, supervisor], now=300)["eligible_adjudications"]
    report = eligible_feedback([row, supervisor], now=1_000_000)
    assert len(report["eligible_adjudications"]) == 1
    assert report["automatic_promotion"] is False
    assert report["transaction_label_conversion"] is False
    assert not eligible_feedback([row, dict(supervisor, fraudulent=False)], now=1_000_000)["eligible_adjudications"]
    path = tmp_path / "feedback.json"
    path.write_text(json.dumps([row, supervisor]), encoding="utf-8")
    output = tmp_path / "filtered.json"
    monkeypatch.setattr("sys.argv", ["retrain_from_feedback", "--feedback", str(path), "--out", str(output), "--as-of", "1000000"])
    main()
    assert json.loads(output.read_text()) == report
