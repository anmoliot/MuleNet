import math
import random

import pytest
from feature_service import online_snapshot
from mulenet_core.features import OnlineFeatureStore, extract_features
from mulenet_core.graph import FeatureBudgetExceeded, canonical_events, transaction_graph
from mulenet_core.schema import Account, FeatureConfig, Transaction, feature_names, feature_schema_hash
from pydantic import ValidationError
from simulation.generator import SimulationConfig, generate
from training.build_dataset import build_examples


def event(identifier, source, target, ts, amount, **kwargs):
    return Transaction(transaction_id=identifier, source=source, target=target, ts=ts, amount=float(amount), **kwargs)


def test_offline_online_parity_for_1000_random_asof_points(record_property):
    rng = random.Random(90210)
    config = SimulationConfig(components=3, accounts_per_component=10, days=7, noise_events_per_day=1)
    dataset = generate(config)
    end = max(e.ts for e in dataset.transactions)
    points = [
        (rng.choice(dataset.accounts).account_id, rng.randrange(config.base_time, end - 3600)) for _ in range(1000)
    ]
    offline = build_examples(dataset, points, horizon=3600, complete_through=end)
    shuffled = list(dataset.transactions)
    rng.shuffle(shuffled)
    online = OnlineFeatureStore(accounts=dataset.accounts)
    for transaction in shuffled + shuffled[:20]:
        online.ingest(transaction)
    for expected in offline:
        assert online.snapshot(expected.account_id, expected.as_of) == pytest.approx(expected.features, abs=1e-9, rel=0)
    record_property("parity_points", len(points))


def test_feature_http_contract_is_authenticated_and_matches_offline(monkeypatch):
    from fastapi.testclient import TestClient
    from feature_service import create_app

    monkeypatch.delenv("MULENET_SERVICE_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SERVICE_SECRET"):
        create_app()
    import time

    import jwt

    secret = "unit-test-only-" + "s" * 64
    monkeypatch.setenv("MULENET_SERVICE_SECRET", secret)
    token = jwt.encode(
        {
            "iss": "mulenet-backend",
            "aud": "mulenet-ml",
            "sub": "backend",
            "tenant": "fixture",
            "scope": "features",
            "iat": int(time.time()),
            "exp": int(time.time()) + 30,
            "jti": "fixture-request",
        },
        secret,
        algorithm="HS256",
    )
    with TestClient(create_app()) as client:
        payload = {"events": [event("1", "a", "b", 100, 10).model_dump()], "account_id": "b", "as_of": 100}
        assert client.post("/features", json=payload).status_code == 401
        assert client.post("/features", json=payload, headers={"Authorization": "Bearer arbitrary"}).status_code == 401
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/features", json=payload, headers=headers)
        assert response.status_code == 200
        assert response.json()["features"] == extract_features([event("1", "a", "b", 100, 10)], "b", 100)
        assert response.json()["feature_schema_hash"] == feature_schema_hash()
        assert (
            client.post(
                "/features", json={**payload, "config": FeatureConfig().model_dump(mode="json")}, headers=headers
            ).status_code
            == 200
        )
        assert client.post("/features", json={**payload, "as_of": "100"}, headers=headers).status_code == 422


def test_hand_computed_ratios_entropy_dwell_and_repeated_edges():
    events = [
        event("1", "a", "b", 100, 100),
        event("2", "c", "b", 110, 300),
        event("3", "b", "d", 120, 200),
        event("4", "b", "d", 130, 100),
    ]
    features = extract_features(events, "b", 130)
    assert features["in_degree_3600s"] == 2
    assert features["out_degree_3600s"] == 2
    assert features["unique_out_3600s"] == 1
    assert features["pass_through_ratio_3600s"] == 0.75
    assert features["log_sent_3600s"] == math.log1p(300)
    assert features["counterparty_entropy_3600s"] == pytest.approx(-0.25 * math.log2(0.25) - 0.75 * math.log2(0.75))
    assert features["dwell_seconds_3600s"] == 20
    graph = transaction_graph(events, FeatureConfig())
    assert graph.number_of_edges() == 4


def test_future_edges_labels_and_typologies_cannot_change_features():
    past = [event("1", "a", "b", 100, 100)]
    future = event("2", "b", "c", 101, 1e9, fraud=True, typology="layering")
    assert online_snapshot(past + [future], "b", 100) == online_snapshot(past, "b", 100)
    relabeled = [past[0].model_copy(update={"fraud": True, "typology": "cycle", "ring_id": "secret"})]
    assert extract_features(past, "b", 100) == extract_features(relabeled, "b", 100)
    assert extract_features(past, "b", 100)["pass_through_ratio_3600s"] == 0


def test_boundary_cold_start_sharing_cycles_and_balances():
    events = [
        event("old", "a", "b", 100, 999),
        event(
            "1",
            "b",
            "c",
            3700,
            49000,
            device_id="d",
            ip_address="ip",
            sender_balance_before=50000.0,
            sender_balance_after=1000.0,
        ),
        event("2", "c", "b", 3700, 1000, device_id="d", ip_address="ip"),
    ]
    feature = extract_features(events, "b", 3700)
    assert feature["log_recv_3600s"] == math.log1p(1000)  # ts=100 excluded at left boundary
    assert feature["cycle_count_3600s"] == 1
    assert feature["device_sharing_degree_3600s"] == 1
    assert feature["ip_sharing_degree_3600s"] == 1
    assert feature["structuring_score_3600s"] == 1
    assert feature["balance_delta_error_3600s"] == 0
    assert feature["balance_delta_observed_3600s"] == 1
    cold = extract_features([], "new", 3700)
    assert set(cold) == set(feature_names())
    assert all(value == 0 for value in cold.values())


def test_strict_schema_duplicate_conflict_and_resource_budget():
    with pytest.raises(ValidationError):
        event("1", "a", "b", "100", -1)
    with pytest.raises(ValidationError):
        event("1", "a", "b", 100, float("nan"))
    with pytest.raises(ValueError, match="Conflicting"):
        canonical_events([event("1", "a", "b", 100, 1), event("1", "a", "b", 100, 2)])
    with pytest.raises(FeatureBudgetExceeded):
        extract_features(
            [event("1", "a", "b", 100, 1), event("2", "b", "c", 100, 2)], "b", 100, FeatureConfig(max_graph_nodes=2)
        )
    assert feature_schema_hash() != feature_schema_hash(FeatureConfig(currency="USD"))


def test_additional_feature_oracles_and_metadata_absence():
    transactions = [
        event("old", "a", "b", 100, 100),
        event("1", "a", "b", 4000, 1000),
        event("2", "a", "c", 4010, 2000),
        event("3", "b", "d", 4020, 3000),
        event("4", "d", "e", 4030, 4000),
    ]
    result = extract_features(transactions, "a", 4040, accounts={"a": Account(account_id="a", created_at=0)})
    assert result["account_age_seconds"] == 4040 and result["account_age_known"] == 1
    assert result["new_payee_ratio_3600s"] == 0.5
    assert result["round_amount_ratio_3600s"] == 1
    assert result["out_flow_hop1_3600s"] == math.log1p(3000)
    assert result["out_flow_hop2_3600s"] == math.log1p(3000)
    assert result["out_flow_hop3_3600s"] == math.log1p(4000)
    assert result["fan_out_ratio_3600s"] == 2
    assert result["velocity_zscore_3600s"] > 0
    assert result["device_observed_3600s"] == result["balance_delta_observed_3600s"] == 0
    assert 0 < result["pagerank_3600s"] < 1
    cycle = [event("a", "a", "b", 100, 10), event("b", "b", "c", 110, 10), event("c", "c", "a", 120, 10)]
    triangle = extract_features(cycle, "a", 130)
    assert triangle["cycle_count_3600s"] == 1
    assert triangle["clustering_3600s"] == 1
    assert triangle["pagerank_3600s"] == pytest.approx(1 / 3)
    with pytest.raises(ValueError, match="predates"):
        extract_features(transactions, "a", 4040, accounts={"a": Account(account_id="a", created_at=200)})
    with pytest.raises(FeatureBudgetExceeded, match="Cycle"):
        extract_features(cycle + [event("d", "b", "a", 125, 10)], "a", 130, FeatureConfig(max_cycles=1))
