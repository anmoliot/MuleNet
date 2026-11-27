import numpy as np
import pytest
import skops.io as sio
import torch
from mulenet_core.models import ModelBundle, load_skops
from mulenet_core.schema import FeatureConfig
from simulation.generator import SimulationConfig, generate
from training.experiment import prepare, train_experiment
from training.train_gnn import TemporalGAT, predict_graphs
from training.train_tabular import select_threshold


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    directory = tmp_path_factory.mktemp("safe-models") / "version"
    dataset = generate(SimulationConfig(components=6, accounts_per_component=10, days=18, noise_events_per_day=2))
    config = FeatureConfig()
    training = train_experiment(dataset, "sim", "temporal", directory, config, epochs=8)
    return directory, dataset, config, training


def test_real_gnn_uses_edges_and_exports_dynamic_shapes():
    torch.manual_seed(1)
    model = TemporalGAT(4).eval()
    x = torch.tensor([[1.0, 2.0, 3.0, 4.0], [7.0, 1.0, 8.0, 2.0], [3.0, 8.0, 1.0, 9.0]])
    edges = torch.tensor([[0, 1, 2], [1, 2, 0]])
    attributes = torch.ones(3, 3)
    assert not torch.allclose(
        model(x, edges, attributes), model(x, torch.empty(2, 0, dtype=torch.long), torch.empty(0, 3))
    )


def test_safe_bundle_calibration_explanation_and_schema(trained):
    directory, dataset, config, training = trained
    with pytest.raises(ValueError, match="allow-synthetic"):
        ModelBundle(directory)
    with pytest.raises(ValueError, match="schema"):
        ModelBundle(directory, FeatureConfig(currency="USD"), allow_synthetic=True)
    bundle = ModelBundle(directory, config, allow_synthetic=True)
    split, graphs = prepare(dataset, "temporal", config)
    assert bundle.drift_reference.source_split == "TRAIN"
    assert bundle.drift_reference.train_rows == len(split.train)
    train_vectors = {tuple(row.features[name] for name in bundle.names) for row in split.train}
    assert set(bundle.drift_reference.features) <= train_vectors
    gnn = predict_graphs(bundle.gnn, graphs["test"])
    probabilities = bundle.predict(
        [row.features for row in split.test], [gnn[(row.account_id, row.as_of)] for row in split.test]
    )
    assert set(probabilities) == {"tabular", "tabular_graph", "gnn", "anomaly_signal", "fusion"}
    assert all(np.isfinite(value).all() for value in probabilities.values())
    assert training["gnn"]["training"].startswith("PyG NeighborLoader")
    assert bundle.explain_tabular(split.test[0].features)
    assert isinstance(torch.load(directory / "gnn-state.pt", weights_only=True), dict)
    assert torch.isfinite(
        bundle.gnn(torch.zeros(1, len(bundle.names)), torch.empty(2, 0, dtype=torch.long), torch.empty(0, 3))
    ).all()
    from explain import explain_graph

    graph = next(iter(graphs["test"].values()))
    assert explain_graph(bundle, graph, 0, epochs=2)["edges"]
    with pytest.raises(ValueError, match="schema"):
        bundle.matrix([{"out_degree": 5}])
    with pytest.raises(FileExistsError):
        train_experiment(dataset, "sim", "temporal", directory, config)


def test_integrity_rejected_before_loading_and_skops_never_trusts_all(trained, tmp_path):
    directory, _, config, _ = trained
    path = directory / "tabular.ubj"
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"tampered")
        with pytest.raises(ValueError, match="integrity"):
            ModelBundle(directory, config, allow_synthetic=True)
    finally:
        path.write_bytes(original)
    from types import SimpleNamespace

    suspicious = tmp_path / "unapproved.skops"
    sio.dump(SimpleNamespace(command="never execute"), suspicious)
    with pytest.raises(ValueError, match="unapproved"):
        load_skops(suspicious)


def test_threshold_uses_only_supplied_validation_arrays():
    truth = np.array([0, 0, 1, 1])
    scores = np.array([0.2, 0.8, 0.3, 0.9])
    threshold = select_threshold(truth, scores, max_fpr=0)
    assert not (scores[truth == 0] >= threshold).any()
    assert threshold == 0.9


def test_missing_or_tampered_drift_reference_is_rejected_before_model_loading(trained):
    directory, _, config, _ = trained
    path = directory / "drift-reference.json"
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"tampered")
        with pytest.raises(ValueError, match="integrity"):
            ModelBundle(directory, config, allow_synthetic=True)
        path.unlink()
        with pytest.raises(ValueError, match="integrity"):
            ModelBundle(directory, config, allow_synthetic=True)
    finally:
        path.write_bytes(original)


def test_drift_is_measured_and_missing_samples_fail():
    from drift import distribution_shift

    baseline = np.arange(100, dtype=float)
    assert distribution_shift(baseline, baseline)["psi"] == 0
    assert distribution_shift(baseline, baseline + 100)["review_trigger"]
    assert distribution_shift(np.ones(100), np.ones(100) * 2)["review_trigger"]
    with pytest.raises(ValueError, match="finite"):
        distribution_shift([], baseline)
