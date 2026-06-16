"""
ml_models.py — Real ML Scoring Models for MuleNet
Layer 5A: XGBoost classifier trained on synthetic mule account patterns
Layer 5B: Graph Neural Scoring via iterative message-passing (real GNN-like inference)

NO MOCKS — these are real trained models.
"""

import numpy as np
import os
import pickle
import math
from typing import Dict, List, Tuple, Any
from pathlib import Path

# ── Try importing xgboost; fall back to sklearn GradientBoosting ─────────────
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

MODEL_DIR = Path(__file__).parent / "trained_models"
MODEL_DIR.mkdir(exist_ok=True)

FAST_PATH_MODEL_PATH = MODEL_DIR / "fast_path_model.pkl"
FAST_PATH_SCALER_PATH = MODEL_DIR / "fast_path_scaler.pkl"
GNN_WEIGHTS_PATH = MODEL_DIR / "gnn_weights.pkl"

# Feature order used by the fast-path model
FEATURE_COLS = [
    "out_degree", "in_degree", "total_sent", "total_recv",
    "pass_through_rate", "fan_out_ratio", "counterparty_entropy",
    "share_of_total_flow",
]


# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHETIC DATA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_training_data(n_samples: int = 5000, seed: int = 42) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate realistic synthetic labeled data for mule account detection.
    Positive class (mule=1): high pass-through, high fan-out, specific entropy patterns.
    Negative class (mule=0): normal banking behavior.
    """
    rng = np.random.RandomState(seed)

    X_list = []
    y_list = []

    n_mules = int(n_samples * 0.3)   # 30% mules (class imbalance intentional)
    n_legit = n_samples - n_mules

    # ── Legitimate accounts ──
    for _ in range(n_legit):
        out_deg = rng.poisson(1.5)
        in_deg = rng.poisson(1.5)
        total_sent = rng.exponential(15000) * max(out_deg, 1)
        total_recv = rng.exponential(15000) * max(in_deg, 1)
        pass_through = min(abs(rng.normal(0.2, 0.15)), 1.0)
        fan_out = out_deg / (in_deg + 1)
        entropy = abs(rng.normal(0.5, 0.3))
        share = abs(rng.normal(0.1, 0.08))
        X_list.append([out_deg, in_deg, total_sent, total_recv,
                        pass_through, fan_out, entropy, share])
        y_list.append(0)

    # ── Mule accounts ── (distinct behavioral signature)
    for _ in range(n_mules):
        # Mules receive and rapidly distribute: high in+out degree
        out_deg = rng.poisson(4) + 2
        in_deg = rng.poisson(2) + 1
        total_recv = rng.exponential(50000) + 20000
        # Mules pass through most of what they receive
        pass_through = min(0.6 + abs(rng.normal(0.2, 0.1)), 1.0)
        total_sent = total_recv * pass_through
        fan_out = out_deg / (in_deg + 1)
        # Higher entropy = distributing to many different accounts
        entropy = abs(rng.normal(1.2, 0.4))
        share = abs(rng.normal(0.3, 0.15))
        X_list.append([out_deg, in_deg, total_sent, total_recv,
                        pass_through, fan_out, entropy, share])
        y_list.append(1)

    # Shuffle
    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int32)
    perm = rng.permutation(len(y))
    return X[perm], y[perm]


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5A — FAST PATH: XGBoost / Gradient Boosting
# ═══════════════════════════════════════════════════════════════════════════════

class FastPathModel:
    """
    Real gradient-boosted tree model for mule detection.
    Trains on synthetic data if no saved model exists.
    """

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self._load_or_train()

    def _load_or_train(self):
        if FAST_PATH_MODEL_PATH.exists() and FAST_PATH_SCALER_PATH.exists():
            with open(FAST_PATH_MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)
            with open(FAST_PATH_SCALER_PATH, "rb") as f:
                self.scaler = pickle.load(f)
            print("[FastPath] Loaded trained model from disk.")
        else:
            self._train()

    def _train(self):
        print("[FastPath] Training XGBoost model on synthetic data...")
        X, y = _generate_training_data(n_samples=5000)
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)

        if HAS_XGB:
            self.model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                eval_metric="logloss",
                use_label_encoder=False,
                random_state=42,
            )
        else:
            self.model = GradientBoostingClassifier(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42,
            )

        self.model.fit(X_scaled, y)
        print(f"[FastPath] Training complete. Accuracy: "
              f"{self.model.score(X_scaled, y):.4f}")

        # Save
        with open(FAST_PATH_MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(FAST_PATH_SCALER_PATH, "wb") as f:
            pickle.dump(self.scaler, f)
        print("[FastPath] Model saved to disk.")

    def predict(self, features: Dict[str, Dict]) -> Dict[str, float]:
        """
        Score each account using the trained model.
        Returns {account_id: mule_probability}.
        """
        if not features:
            return {}

        acct_ids = list(features.keys())
        X = np.array([
            [features[a].get(col, 0) for col in FEATURE_COLS]
            for a in acct_ids
        ], dtype=np.float64)

        X_scaled = self.scaler.transform(X)
        probs = self.model.predict_proba(X_scaled)[:, 1]  # P(mule=1)

        return {acct: round(float(prob), 4) for acct, prob in zip(acct_ids, probs)}

    def retrain(self, feedback_samples: List[Dict[str, Any]]):
        """
        Retrain XGBoost using original synthetic data augmented with investigator feedback.
        feedback_samples is a list of dicts: [{'features': [...], 'label': int}]
        """
        print(f"[FastPath] Retraining with {len(feedback_samples)} investigator feedback samples...")
        X_base, y_base = _generate_training_data(n_samples=5000)
        
        if feedback_samples:
            X_feed = np.array([f['features'] for f in feedback_samples], dtype=np.float64)
            y_feed = np.array([f['label'] for f in feedback_samples], dtype=np.int32)
            
            # Oversample feedback to ensure it shifts the decision boundary
            X_feed_rep = np.repeat(X_feed, 50, axis=0)
            y_feed_rep = np.repeat(y_feed, 50, axis=0)
            
            X = np.vstack([X_base, X_feed_rep])
            y = np.concatenate([y_base, y_feed_rep])
        else:
            X, y = X_base, y_base
            
        self.scaler = StandardScaler()
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        self.model.fit(X_scaled, y)
        print(f"[FastPath] Retraining complete. Accuracy: {self.model.score(X_scaled, y):.4f}")
        
        with open(FAST_PATH_MODEL_PATH, "wb") as f:
            pickle.dump(self.model, f)
        with open(FAST_PATH_SCALER_PATH, "wb") as f:
            pickle.dump(self.scaler, f)
        print("[FastPath] Model updated and saved to disk.")

    def feature_importance(self) -> Dict[str, float]:
        """Return feature importance scores."""
        if hasattr(self.model, "feature_importances_"):
            imp = self.model.feature_importances_
            return {col: round(float(v), 4) for col, v in zip(FEATURE_COLS, imp)}
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# LAYER 5B — DEEP PATH: Graph Neural Scoring (Message-Passing)
# ═══════════════════════════════════════════════════════════════════════════════

class GraphNeuralScorer:
    """
    Real graph neural network-style scoring using iterative message-passing.
    Implements a 2-layer Graph Attention mechanism:
      1. Aggregate neighbor features weighted by edge amounts
      2. Apply learned attention weights to produce risk embeddings
      3. Score via sigmoid on final embeddings

    Weights are trained on synthetic graph patterns if no saved model exists.
    """

    def __init__(self):
        self.W1 = None  # Layer 1 weights: (input_dim, hidden_dim)
        self.W2 = None  # Layer 2 weights: (hidden_dim, 1)
        self.attention = None  # Attention vector: (hidden_dim,)
        self.input_dim = len(FEATURE_COLS) + 3  # features + PageRank + degree_centrality + betweenness
        self.hidden_dim = 16
        self._load_or_train()

    def _load_or_train(self):
        if GNN_WEIGHTS_PATH.exists():
            with open(GNN_WEIGHTS_PATH, "rb") as f:
                weights = pickle.load(f)
            self.W1 = weights["W1"]
            self.W2 = weights["W2"]
            self.attention = weights["attention"]
            print("[GNN] Loaded trained weights from disk.")
        else:
            self._train()

    def _train(self):
        """
        Train GNN weights on synthetic graph patterns.
        Uses a simple supervised approach: generate graphs with known mule topologies,
        run message passing, and optimize weights via gradient descent.
        """
        print("[GNN] Training graph neural network weights...")
        rng = np.random.RandomState(42)

        # Xavier initialization
        self.W1 = rng.randn(self.input_dim, self.hidden_dim) * np.sqrt(2.0 / self.input_dim)
        self.W2 = rng.randn(self.hidden_dim, 1) * np.sqrt(2.0 / self.hidden_dim)
        self.attention = rng.randn(self.hidden_dim) * 0.1

        # Generate training graphs
        lr = 0.01
        n_epochs = 100
        n_graphs = 50

        for epoch in range(n_epochs):
            total_loss = 0.0
            for _ in range(n_graphs):
                G, node_features, labels = self._generate_training_graph(rng)
                if len(node_features) == 0:
                    continue

                # Forward pass
                nodes = list(node_features.keys())
                X = np.array([node_features[n] for n in nodes])
                y = np.array([labels.get(n, 0) for n in nodes], dtype=np.float64)

                # Message passing: aggregate neighbor features
                X_agg = self._message_pass(G, nodes, X)

                # Layer 1: ReLU(X_agg @ W1)
                H = X_agg @ self.W1
                H = np.maximum(H, 0)  # ReLU

                # Attention-weighted aggregation (self-attention)
                attn_scores = H @ self.attention
                attn_weights = 1.0 / (1.0 + np.exp(-attn_scores))  # sigmoid
                H_attn = H * attn_weights[:, np.newaxis]

                # Layer 2: sigmoid(H_attn @ W2)
                logits = (H_attn @ self.W2).flatten()
                preds = 1.0 / (1.0 + np.exp(-logits))

                # Binary cross-entropy loss
                eps = 1e-7
                loss = -np.mean(y * np.log(preds + eps) + (1 - y) * np.log(1 - preds + eps))
                total_loss += loss

                # Backward pass (simplified gradient descent)
                d_preds = (preds - y) / len(y)
                d_logits = d_preds * preds * (1 - preds)

                # Gradient for W2
                d_W2 = H_attn.T @ d_logits[:, np.newaxis]

                # Gradient for attention
                d_H_attn = d_logits[:, np.newaxis] @ self.W2.T
                d_attn_weights = np.sum(d_H_attn * H, axis=1)
                d_attn_sigmoid = d_attn_weights * attn_weights * (1 - attn_weights)
                d_attention = H.T @ d_attn_sigmoid

                # Gradient for W1 (through ReLU)
                d_H = d_H_attn * attn_weights[:, np.newaxis]
                d_H[X_agg @ self.W1 <= 0] = 0  # ReLU derivative
                d_W1 = X_agg.T @ d_H

                # Update weights
                self.W1 -= lr * np.clip(d_W1, -1, 1)
                self.W2 -= lr * np.clip(d_W2, -1, 1)
                self.attention -= lr * np.clip(d_attention, -1, 1)

            if (epoch + 1) % 25 == 0:
                print(f"  Epoch {epoch + 1}/{n_epochs}, Loss: {total_loss / n_graphs:.4f}")

        # Save weights
        with open(GNN_WEIGHTS_PATH, "wb") as f:
            pickle.dump({
                "W1": self.W1,
                "W2": self.W2,
                "attention": self.attention,
            }, f)
        print("[GNN] Training complete. Weights saved to disk.")

    def _generate_training_graph(self, rng) -> Tuple:
        """Generate a synthetic graph with labeled mule/legit nodes."""
        import networkx as nx

        G = nx.DiGraph()
        n_nodes = rng.randint(5, 15)
        labels = {}
        node_features = {}

        # Create nodes
        for i in range(n_nodes):
            node_id = f"n{i}"
            is_mule = rng.random() < 0.3

            out_deg = rng.poisson(4 if is_mule else 1.5)
            in_deg = rng.poisson(2 if is_mule else 1.5)
            total_sent = rng.exponential(50000 if is_mule else 15000)
            total_recv = rng.exponential(60000 if is_mule else 15000)
            pass_through = min(0.7 + rng.normal(0, 0.1), 1.0) if is_mule else max(rng.normal(0.2, 0.15), 0)
            fan_out = out_deg / (in_deg + 1)
            entropy = abs(rng.normal(1.2 if is_mule else 0.5, 0.3))
            share = abs(rng.normal(0.3 if is_mule else 0.1, 0.1))

            # Graph centrality features (placeholder)
            pagerank = rng.exponential(0.1 if is_mule else 0.05)
            degree_cent = (out_deg + in_deg) / (2 * n_nodes)
            betweenness = rng.exponential(0.15 if is_mule else 0.05)

            node_features[node_id] = [
                out_deg, in_deg, total_sent / 100000, total_recv / 100000,
                pass_through, fan_out, entropy, share,
                pagerank, degree_cent, betweenness
            ]
            labels[node_id] = 1 if is_mule else 0
            G.add_node(node_id)

        # Create edges
        for i in range(n_nodes):
            n_edges = rng.randint(0, min(3, n_nodes - 1))
            targets = rng.choice(
                [j for j in range(n_nodes) if j != i],
                size=min(n_edges, n_nodes - 1),
                replace=False
            )
            for t in targets:
                G.add_edge(f"n{i}", f"n{t}", amount=rng.exponential(20000))

        return G, node_features, labels

    def _message_pass(self, G, nodes, X):
        """
        Single-round message passing: aggregate neighbor features.
        Applies Time-Decayed Attention (Gap 4) based on edge timestamps:
          weight = amount * exp(-lambda * dt)
        """
        import networkx as nx
        import datetime

        X_agg = np.copy(X)
        node_idx = {n: i for i, n in enumerate(nodes)}
        current_time = datetime.datetime.utcnow()

        def parse_ts(ts_str):
            if not ts_str:
                return None
            try:
                return datetime.datetime.fromisoformat(ts_str.replace('Z', ''))
            except Exception:
                return None

        for i, node in enumerate(nodes):
            neighbor_features = []
            weights = []

            for pred in G.predecessors(node):
                if pred in node_idx:
                    edge_data = G[pred][node]
                    amount = edge_data.get("amount", 1.0)
                    ts = parse_ts(edge_data.get("timestamp"))
                    if ts:
                        # Exponential decay: lambda = 1e-5 (half-life of ~20 hours)
                        dt = (current_time - ts).total_seconds()
                        amount = amount * math.exp(-1e-5 * max(dt, 0.0))
                    neighbor_features.append(X[node_idx[pred]])
                    weights.append(amount)

            for succ in G.successors(node):
                if succ in node_idx:
                    edge_data = G[node][succ]
                    amount = edge_data.get("amount", 1.0)
                    ts = parse_ts(edge_data.get("timestamp"))
                    if ts:
                        dt = (current_time - ts).total_seconds()
                        amount = amount * math.exp(-1e-5 * max(dt, 0.0))
                    neighbor_features.append(X[node_idx[succ]])
                    weights.append(amount)

            if neighbor_features:
                weights = np.array(weights)
                weights = weights / (weights.sum() + 1e-9)  # normalize
                agg = np.average(neighbor_features, axis=0, weights=weights)
                X_agg[i] = 0.5 * X[i] + 0.5 * agg  # combine self + neighbors

        return X_agg

    def predict(self, G, features: Dict[str, Dict]) -> Dict[str, float]:
        """
        Score accounts using trained GNN weights with real message-passing
        over the actual transaction graph.
        """
        import networkx as nx

        if not features:
            return {}

        # Compute graph-level centrality features
        try:
            pagerank = nx.pagerank(G, weight=None, max_iter=100)
        except Exception:
            pagerank = {n: 0 for n in G.nodes()}

        try:
            degree_cent = nx.degree_centrality(G)
        except Exception:
            degree_cent = {n: 0 for n in G.nodes()}

        try:
            betweenness = nx.betweenness_centrality(G)
        except Exception:
            betweenness = {n: 0 for n in G.nodes()}

        # Build feature matrix
        acct_ids = list(features.keys())
        nodes = [f"account:{a}" for a in acct_ids]

        X = np.array([
            [
                features[a].get(col, 0) for col in FEATURE_COLS
            ] + [
                pagerank.get(f"account:{a}", 0) * 100,
                degree_cent.get(f"account:{a}", 0),
                betweenness.get(f"account:{a}", 0),
            ]
            for a in acct_ids
        ], dtype=np.float64)

        # Normalize amounts for numerical stability
        for col_idx in [2, 3]:  # total_sent, total_recv
            col_max = X[:, col_idx].max()
            if col_max > 0:
                X[:, col_idx] = X[:, col_idx] / col_max

        # Message passing over the real graph
        X_agg = self._message_pass(G, nodes, X)

        # Forward pass through trained network
        H = X_agg @ self.W1
        H = np.maximum(H, 0)  # ReLU

        attn_scores = H @ self.attention
        attn_weights = 1.0 / (1.0 + np.exp(-np.clip(attn_scores, -10, 10)))
        H_attn = H * attn_weights[:, np.newaxis]

        logits = (H_attn @ self.W2).flatten()
        preds = 1.0 / (1.0 + np.exp(-np.clip(logits, -10, 10)))  # sigmoid

        return {acct: round(float(p), 4) for acct, p in zip(acct_ids, preds)}

    def retrain(self, feedback_graphs: List[Tuple[Any, List[List[float]], List[int]]]):
        """
        Fine-tune GNN weights using investigator feedback.
        Each graph is a tuple: (G, X_matrix, y_vector)
        """
        if not feedback_graphs:
            print("[GNN] No feedback graphs provided for retraining.")
            return

        print(f"[GNN] Fine-tuning model weights with {len(feedback_graphs)} feedback graphs...")
        lr = 0.005
        n_epochs = 20
        
        for epoch in range(n_epochs):
            total_loss = 0.0
            count = 0
            for G, X, y in feedback_graphs:
                if len(X) == 0:
                    continue
                
                # Forward
                nodes = [f"account:{node_id}" for node_id in G.nodes()]
                X_arr = np.array(X, dtype=np.float64)
                y_arr = np.array(y, dtype=np.float64)
                
                X_agg = self._message_pass(G, nodes, X_arr)
                H = X_agg @ self.W1
                H = np.maximum(H, 0)
                
                attn_scores = H @ self.attention
                attn_weights = 1.0 / (1.0 + np.exp(-np.clip(attn_scores, -10, 10)))
                H_attn = H * attn_weights[:, np.newaxis]
                
                logits = (H_attn @ self.W2).flatten()
                preds = 1.0 / (1.0 + np.exp(-np.clip(logits, -10, 10)))
                
                loss = -np.mean(y_arr * np.log(preds + 1e-7) + (1 - y_arr) * np.log(1 - preds + 1e-7))
                total_loss += loss
                count += 1
                
                # Backward
                d_preds = (preds - y_arr) / len(y_arr)
                d_logits = d_preds * preds * (1 - preds)
                d_W2 = H_attn.T @ d_logits[:, np.newaxis]
                d_H_attn = d_logits[:, np.newaxis] @ self.W2.T
                d_attn_weights = np.sum(d_H_attn * H, axis=1)
                d_attn_sigmoid = d_attn_weights * attn_weights * (1 - attn_weights)
                d_attention = H.T @ d_attn_sigmoid
                d_H = d_H_attn * attn_weights[:, np.newaxis]
                d_H[X_agg @ self.W1 <= 0] = 0
                d_W1 = X_agg.T @ d_H
                
                self.W1 -= lr * np.clip(d_W1, -1, 1)
                self.W2 -= lr * np.clip(d_W2, -1, 1)
                self.attention -= lr * np.clip(d_attention, -1, 1)

        # Save weights
        with open(GNN_WEIGHTS_PATH, "wb") as f:
            pickle.dump({
                "W1": self.W1,
                "W2": self.W2,
                "attention": self.attention,
            }, f)
        print("[GNN] Fine-tuning complete. Weights saved to disk.")



# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON MODEL INSTANCES (loaded once at startup)
# ═══════════════════════════════════════════════════════════════════════════════

_fast_path: FastPathModel = None
_gnn_scorer: GraphNeuralScorer = None


def get_fast_path() -> FastPathModel:
    global _fast_path
    if _fast_path is None:
        _fast_path = FastPathModel()
    return _fast_path


def get_gnn_scorer() -> GraphNeuralScorer:
    global _gnn_scorer
    if _gnn_scorer is None:
        _gnn_scorer = GraphNeuralScorer()
    return _gnn_scorer


# ═══════════════════════════════════════════════════════════════════════════════
# UNSUPERVISED ANOMALY DETECTION LAYER (Isolation Forest)
# ═══════════════════════════════════════════════════════════════════════════

from sklearn.ensemble import IsolationForest

class IsolationForestAnomalyDetector:
    """
    Unsupervised Anomaly Detection using Isolation Forest (Gap 7).
    Helps detect previously unseen mule patterns and out-of-distribution behaviors.
    """
    def __init__(self):
        self.model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
        self._train()

    def _train(self):
        print("[AnomalyDetector] Training unsupervised Isolation Forest...")
        X, _ = _generate_training_data(n_samples=2000)
        self.model.fit(X)
        print("[AnomalyDetector] Unsupervised training complete.")

    def predict(self, features: Dict[str, Dict]) -> Dict[str, float]:
        if not features:
            return {}

        acct_ids = list(features.keys())
        X = np.array([
            [features[a].get(col, 0) for col in FEATURE_COLS]
            for a in acct_ids
        ], dtype=np.float64)

        # score_samples returns negative values (lower = more anomalous)
        scores = self.model.score_samples(X)
        
        # Map raw scores to anomaly probability in range [0, 1]
        anomaly_scores = {}
        for acct, score in zip(acct_ids, scores):
            # Normal scores are around -0.4 to -0.5, anomalies are < -0.65
            norm_anomaly = min(max((-score - 0.35) / 0.3, 0.0), 1.0)
            anomaly_scores[acct] = round(float(norm_anomaly), 4)

        return anomaly_scores

    def retrain(self, feedback_samples: List[Dict[str, Any]]):
        """Include investigator feedback features in training set."""
        X_base, _ = _generate_training_data(n_samples=2000)
        if feedback_samples:
            X_feed = np.array([f['features'] for f in feedback_samples], dtype=np.float64)
            X = np.vstack([X_base, X_feed])
        else:
            X = X_base
        self.model.fit(X)
        print("[AnomalyDetector] Isolation Forest retrained.")


_anomaly_detector: IsolationForestAnomalyDetector = None

def get_anomaly_detector() -> IsolationForestAnomalyDetector:
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = IsolationForestAnomalyDetector()
    return _anomaly_detector


# ═══════════════════════════════════════════════════════════════════════════════
# PLATT CALIBRATION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def calibrate_score(raw_score: float) -> float:
    """
    Applies sigmoid Platt scaling (Gap 9) to convert a raw composite score 
    into a calibrated, probability-like risk metric.
    """
    # Sigmoid mapping centered at 45.0 with steepness 0.08
    scaled = 100.0 / (1.0 + math.exp(-0.08 * (raw_score - 45.0)))
    return min(round(scaled, 2), 100.0)


def get_model_metadata() -> Dict[str, Any]:
    """Return metadata about loaded models for governance/monitoring."""
    fp = get_fast_path()
    ad = get_anomaly_detector()
    return {
        "fast_path": {
            "type": "XGBoost" if HAS_XGB else "GradientBoosting",
            "n_estimators": 200,
            "feature_importance": fp.feature_importance(),
            "model_path": str(FAST_PATH_MODEL_PATH),
            "trained": FAST_PATH_MODEL_PATH.exists(),
        },
        "gnn": {
            "type": "GraphAttentionNetwork",
            "layers": 2,
            "hidden_dim": 16,
            "input_dim": len(FEATURE_COLS) + 3,
            "model_path": str(GNN_WEIGHTS_PATH),
            "trained": GNN_WEIGHTS_PATH.exists(),
        },
        "anomaly_detector": {
            "type": "IsolationForest",
            "estimators": 100,
            "contamination": 0.1,
            "trained": True,
        }
    }

