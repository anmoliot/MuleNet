"""Actual edge-aware PyG message passing with neighbor-sampled training."""

from __future__ import annotations

import copy
import math

import numpy as np
import torch
from sklearn.metrics import average_precision_score
from torch import nn
from torch_geometric.data import Data
from torch_geometric.loader import NeighborLoader
from torch_geometric.nn import GATv2Conv, JumpingKnowledge

from mulenet_core.features import extract_features
from mulenet_core.schema import feature_names

KINDS = ("TRANSFER", "CASH_OUT", "CASH_IN", "PAYMENT", "DEBIT", "ACH", "Cheque", "Credit Card", "Reinvestment", "Wire", "Bitcoin")


class TemporalGAT(nn.Module):
    def __init__(self, dimensions: int, mean=None, scale=None):
        super().__init__()
        self.register_buffer("mean", torch.zeros(dimensions) if mean is None else torch.as_tensor(mean, dtype=torch.float32))
        self.register_buffer("scale", torch.ones(dimensions) if scale is None else torch.as_tensor(scale, dtype=torch.float32).clamp_min(1))
        self.first = GATv2Conv(dimensions, 16, heads=2, concat=False, edge_dim=3, add_self_loops=False, residual=True)
        self.second = GATv2Conv(16, 16, heads=2, concat=False, edge_dim=3, add_self_loops=False, residual=True)
        self.jumping = JumpingKnowledge("cat")
        self.output = nn.Linear(32, 1)

    def forward(self, x, edge_index, edge_attr):
        normalized = (x - self.mean) / self.scale
        first = torch.relu(self.first(normalized, edge_index, edge_attr))
        second = torch.relu(self.second(first, edge_index, edge_attr))
        return self.output(self.jumping([first, second])).squeeze(-1)


def snapshot_graph(events, rows, config, accounts=()):
    if not rows or len({row.as_of for row in rows}) != 1:
        raise ValueError("A graph snapshot must have one as-of time")
    as_of = rows[0].as_of
    known = {row.account_id: row for row in rows}
    selected = [e for e in events if as_of - max(config.windows) < e.ts <= as_of and e.currency == config.currency]
    nodes = sorted(set(known) | {e.source for e in selected} | {e.target for e in selected})
    if len(nodes) > config.max_graph_nodes or len(selected) > config.max_graph_edges:
        raise ValueError("GNN snapshot exceeds resource bounds")
    index = {node: i for i, node in enumerate(nodes)}
    registry = {a.account_id: a for a in accounts}
    names = feature_names(config)
    features = [known[n].features if n in known else extract_features(events, n, as_of, config, registry) for n in nodes]
    pairs, attributes = [], []
    for edge in selected:
        kind = KINDS.index(edge.kind) / len(KINDS) if edge.kind in KINDS else 1.0
        for source, target, direction in ((edge.source, edge.target, 1), (edge.target, edge.source, -1)):
            pairs.append((index[source], index[target]))
            attributes.append([math.log1p(edge.amount), (as_of - edge.ts) / 86400, kind * direction])
    data = Data(x=torch.tensor([[f[name] for name in names] for f in features], dtype=torch.float32),
                edge_index=torch.tensor(pairs, dtype=torch.long).T.contiguous() if pairs else torch.empty((2, 0), dtype=torch.long),
                edge_attr=torch.tensor(attributes, dtype=torch.float32).reshape(-1, 3),
                y=torch.tensor([known[n].label if n in known else 0 for n in nodes], dtype=torch.float32),
                mask=torch.tensor([n in known for n in nodes], dtype=torch.bool))
    data.account_ids = nodes
    return data


def predict_graphs(model, graphs):
    result = {}
    model.eval()
    with torch.no_grad():
        for as_of, data in graphs.items():
            values = torch.sigmoid(model(data.x, data.edge_index, data.edge_attr)).numpy()
            result.update({(account, as_of): float(value) for account, value, selected in zip(data.account_ids, values, data.mask) if selected})
    return result


def train_gnn(train_graphs, val_graphs, dimensions, seed=42, epochs=30):
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    train_x = torch.cat([g.x[g.mask] for g in train_graphs.values()])
    model = TemporalGAT(dimensions, train_x.mean(0), train_x.std(0))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003, weight_decay=0.001)
    labels = torch.cat([g.y[g.mask] for g in train_graphs.values()])
    if labels.sum() == 0 or labels.sum() == len(labels):
        raise ValueError("GNN training requires both classes")
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=(len(labels) - labels.sum()) / labels.sum())
    best, best_ap, stale = None, -1.0, 0
    # NeighborLoader indexes node attributes; human-readable IDs stay outside it.
    tensor_graphs = [Data(x=g.x, edge_index=g.edge_index, edge_attr=g.edge_attr, y=g.y, mask=g.mask) for g in train_graphs.values()]
    loaders = [NeighborLoader(g, num_neighbors=[12, 12], input_nodes=g.mask, batch_size=64, shuffle=False, num_workers=0) for g in tensor_graphs]
    for epoch in range(epochs):
        model.train()
        for loader in loaders:
            for batch in loader:
                optimizer.zero_grad()
                logits = model(batch.x, batch.edge_index, batch.edge_attr)[:batch.batch_size]
                loss = loss_fn(logits, batch.y[:batch.batch_size])
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimizer.step()
        probabilities = predict_graphs(model, val_graphs)
        truth = [int(g.y[i]) for ts, g in val_graphs.items() for i, n in enumerate(g.account_ids) if g.mask[i]]
        scores = [probabilities[(n, ts)] for ts, g in val_graphs.items() for i, n in enumerate(g.account_ids) if g.mask[i]]
        ap = average_precision_score(truth, scores)
        if ap > best_ap:
            best, best_ap, stale = copy.deepcopy(model.state_dict()), float(ap), 0
            best_epoch = epoch + 1
        else:
            stale += 1
        if stale >= 6:
            break
    model.load_state_dict(best)
    return model.eval(), {"validation_pr_auc": best_ap, "best_epoch": best_epoch, "epochs_run": epoch + 1, "training": "PyG NeighborLoader; train-only snapshot edges"}


def export_gnn(model, example, directory):
    torch.save(model.state_dict(), directory / "gnn-state.pt")
    traced = torch.jit.trace(model, (example.x, example.edge_index, example.edge_attr), check_trace=True)
    torch.jit.save(traced, directory / "gnn.ts")
    restored = torch.jit.load(directory / "gnn.ts", map_location="cpu")
    with torch.no_grad():
        torch.testing.assert_close(restored(example.x, example.edge_index, example.edge_attr), model(example.x, example.edge_index, example.edge_attr))
