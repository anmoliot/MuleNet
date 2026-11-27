"""TreeSHAP and PyG edge-mask attribution, never a claim of causal guilt."""

import torch
from torch_geometric.explain import Explainer, GNNExplainer
from training.train_gnn import TemporalGAT


def explain_graph(bundle, graph, node_index, epochs=20, limit=8):
    if graph.edge_index.shape[1] == 0:
        return {"method": "GNNExplainer", "edges": [], "status": "no_observed_edges"}
    model = TemporalGAT(graph.x.shape[1])
    model.load_state_dict(torch.load(bundle.directory / "gnn-state.pt", map_location="cpu", weights_only=True))
    model.eval()
    explainer = Explainer(
        model=model,
        algorithm=GNNExplainer(epochs=epochs),
        explanation_type="model",
        node_mask_type="attributes",
        edge_mask_type="object",
        model_config={"mode": "binary_classification", "task_level": "node", "return_type": "raw"},
    )
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(42)
        attribution = explainer(graph.x, graph.edge_index, edge_attr=graph.edge_attr, index=node_index)
    order = torch.argsort(attribution.edge_mask, descending=True)[:limit]
    return {
        "method": "GNNExplainer",
        "status": "computed",
        "edges": [
            {
                "source": graph.account_ids[int(graph.edge_index[0, i])],
                "target": graph.account_ids[int(graph.edge_index[1, i])],
                "mask_weight": float(attribution.edge_mask[i]),
            }
            for i in order
        ],
    }
