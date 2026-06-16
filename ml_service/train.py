#!/usr/bin/env python
"""
train.py — Command-line training interface for MuleNet ML models.
Supports:
1. Re-running the synthetic data bootstrapping (XGBoost, GNN, Isolation Forest).
2. Training the XGBoost (FastPath) model on a custom CSV dataset.
3. Training the models from a network transactions CSV and node labels CSV.
"""

import os
import csv
import argparse
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Any

# Ensure we import from the local directory
import sys
sys.path.append(str(Path(__file__).parent))

from ml_models import (
    get_fast_path,
    get_gnn_scorer,
    get_anomaly_detector,
    FEATURE_COLS,
    FAST_PATH_MODEL_PATH,
    FAST_PATH_SCALER_PATH,
    GNN_WEIGHTS_PATH,
    _generate_training_data
)

def run_synthetic_training():
    """Force train all models using the internal synthetic dataset generator."""
    print("=== Force Retraining ML Models with Synthetic Datasets ===")
    
    # 1. XGBoost (FastPath)
    print("\n--- Training XGBoost (FastPath) Model ---")
    fp = get_fast_path()
    # Delete existing model files to trigger retraining on load, or call internal train
    if FAST_PATH_MODEL_PATH.exists():
        os.remove(FAST_PATH_MODEL_PATH)
    if FAST_PATH_SCALER_PATH.exists():
        os.remove(FAST_PATH_SCALER_PATH)
    fp._train()
    
    # 2. Graph Neural Network (DeepPath)
    print("\n--- Training Graph Attention Network (GNN) ---")
    gnn = get_gnn_scorer()
    if GNN_WEIGHTS_PATH.exists():
        os.remove(GNN_WEIGHTS_PATH)
    gnn._train()
    
    # 3. Isolation Forest (Anomaly Detector)
    print("\n--- Training Isolation Forest (Anomaly Detector) ---")
    ad = get_anomaly_detector()
    ad._train()
    
    print("\n[SUCCESS] All models trained and saved to 'trained_models/' successfully!")


def train_xgboost_from_csv(csv_path: str):
    """
    Train the FastPath (XGBoost) model using a custom CSV file.
    The CSV must contain the following columns:
    out_degree, in_degree, total_sent, total_recv, pass_through_rate, fan_out_ratio, counterparty_entropy, share_of_total_flow, label
    """
    path = Path(csv_path)
    if not path.exists():
        print(f"[Error] CSV file not found at: {csv_path}")
        sys.exit(1)

    print(f"=== Training XGBoost from Custom CSV: {csv_path} ===")
    X_list = []
    y_list = []

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        if not headers:
            print("[Error] CSV file is empty.")
            sys.exit(1)

        # Validate headers
        missing_features = [col for col in FEATURE_COLS if col not in headers]
        if missing_features:
            print(f"[Error] CSV is missing required feature columns: {missing_features}")
            print(f"Expected columns: {FEATURE_COLS} + ['label']")
            sys.exit(1)
        
        label_col = "label" if "label" in headers else ("is_mule" if "is_mule" in headers else None)
        if not label_col:
            print("[Error] CSV must have a 'label' or 'is_mule' column.")
            sys.exit(1)

        for row_idx, row in enumerate(reader):
            try:
                features = [float(row[col]) for col in FEATURE_COLS]
                label = int(float(row[label_col]))
                X_list.append(features)
                y_list.append(label)
            except ValueError as e:
                print(f"[Warning] Skipping row {row_idx + 2} due to parsing error: {e}")

    if not X_list:
        print("[Error] No valid training samples parsed from the CSV.")
        sys.exit(1)

    X = np.array(X_list, dtype=np.float64)
    y = np.array(y_list, dtype=np.int32)
    print(f"Loaded {X.shape[0]} samples with {X.shape[1]} features.")

    # Train
    fp = get_fast_path()
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import GradientBoostingClassifier
    try:
        import xgboost as xgb
        HAS_XGB = True
    except ImportError:
        HAS_XGB = False

    print("Fitting Scaler...")
    fp.scaler = StandardScaler()
    fp.scaler.fit(X)
    X_scaled = fp.scaler.transform(X)

    print("Fitting Model...")
    if HAS_XGB:
        fp.model = xgb.XGBClassifier(
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
        fp.model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )

    fp.model.fit(X_scaled, y)
    accuracy = fp.model.score(X_scaled, y)
    print(f"Training Complete. Accuracy on training set: {accuracy:.4f}")

    # Save
    MODEL_DIR = Path(__file__).parent / "trained_models"
    MODEL_DIR.mkdir(exist_ok=True)
    with open(FAST_PATH_MODEL_PATH, "wb") as f:
        pickle.dump(fp.model, f)
    with open(FAST_PATH_SCALER_PATH, "wb") as f:
        pickle.dump(fp.scaler, f)

    print(f"[SUCCESS] Saved model to {FAST_PATH_MODEL_PATH}")
    print(f"[SUCCESS] Saved scaler to {FAST_PATH_SCALER_PATH}")


def train_from_network_csv(edges_csv: str, labels_csv: str):
    """
    Train both XGBoost and GNN from a transaction network CSV and account labels CSV.
    edges_csv columns: sender_account, receiver_account, amount, timestamp
    labels_csv columns: account_id, label (1 for mule, 0 for legit)
    """
    import networkx as nx
    from datetime import datetime

    print(f"=== Training models from Transaction Network ===")
    print(f"Edges: {edges_csv}")
    print(f"Labels: {labels_csv}")

    # 1. Load labels
    labels = {}
    with open(labels_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        acct_col = "account_id" if "account_id" in headers else ("account" if "account" in headers else headers[0])
        label_col = "label" if "label" in headers else ("is_mule" if "is_mule" in headers else headers[1])
        
        for row in reader:
            labels[row[acct_col]] = int(float(row[label_col]))

    # 2. Load transactions and build NetworkX Graph
    G = nx.DiGraph()
    with open(edges_csv, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        sender_col = "sender_account" if "sender_account" in headers else ("sender" if "sender" in headers else headers[0])
        recv_col = "receiver_account" if "receiver_account" in headers else ("receiver" if "receiver" in headers else headers[1])
        amt_col = "amount" if "amount" in headers else headers[2]
        ts_col = "timestamp" if "timestamp" in headers else headers[3]

        for row in reader:
            sender = row[sender_col]
            recv = row[recv_col]
            amount = float(row[amt_col])
            timestamp = row[ts_col]
            
            G.add_node(f"account:{sender}", node_type="account")
            G.add_node(f"account:{recv}", node_type="account")
            G.add_edge(f"account:{sender}", f"account:{recv}", amount=amount, timestamp=timestamp, edge_type="sent_to")

    # 3. Compute network features for labeled accounts
    print(f"Computing graph metrics for {len(labels)} accounts...")
    
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

    # Compute tabular features
    X_xgb_list = []
    y_xgb_list = []
    
    # We will build feedback structure for GNN training
    feedback_graphs = []
    
    # Simple feature calculator for each account
    for acct, label in labels.items():
        node_name = f"account:{acct}"
        if not G.has_node(node_name):
            continue
        
        out_degree = G.out_degree(node_name)
        in_degree = G.in_degree(node_name)
        
        # Calculate flows
        total_sent = sum(d.get("amount", 0.0) for _, _, d in G.out_edges(node_name, data=True))
        total_recv = sum(d.get("amount", 0.0) for _, _, d in G.in_edges(node_name, data=True))
        
        pass_through_rate = min(total_sent / (total_recv + 1e-5), 1.0)
        fan_out_ratio = out_degree / (in_degree + 1.0)
        
        # Counterparty Entropy
        recipients = [v for _, v in G.out_edges(node_name)]
        if recipients:
            counts = {}
            for r in recipients:
                counts[r] = counts.get(r, 0) + 1
            total_edges = len(recipients)
            entropy = -sum((c / total_edges) * np.log(c / total_edges) for c in counts.values())
        else:
            entropy = 0.0
            
        share_of_total_flow = total_sent / (total_sent + total_recv + 1e-5)
        
        feats = [
            out_degree, in_degree, total_sent, total_recv,
            pass_through_rate, fan_out_ratio, entropy, share_of_total_flow
        ]
        
        X_xgb_list.append(feats)
        y_xgb_list.append(label)

    # 4. Train XGBoost Model
    if X_xgb_list:
        X_xgb = np.array(X_xgb_list, dtype=np.float64)
        y_xgb = np.array(y_xgb_list, dtype=np.int32)
        print(f"XGBoost training set shape: {X_xgb.shape}")
        
        fp = get_fast_path()
        from sklearn.preprocessing import StandardScaler
        fp.scaler = StandardScaler()
        fp.scaler.fit(X_xgb)
        X_scaled = fp.scaler.transform(X_xgb)
        
        fp.model.fit(X_scaled, y_xgb)
        print(f"[XGBoost] Accuracy on custom network: {fp.model.score(X_scaled, y_xgb):.4f}")
        
        # Save
        with open(FAST_PATH_MODEL_PATH, "wb") as f:
            pickle.dump(fp.model, f)
        with open(FAST_PATH_SCALER_PATH, "wb") as f:
            pickle.dump(fp.scaler, f)
        print("[SUCCESS] FastPath XGBoost updated.")

    # 5. Train GNN Model (using whole graph feedback iteration)
    gnn_samples = []
    # Build feature arrays for nodes in G
    G_nodes = [n.split(":")[-1] for n in G.nodes() if n.startswith("account:")]
    node_idx = {}
    X_gnn = []
    y_gnn = []
    
    for idx, acct in enumerate(G_nodes):
        node_name = f"account:{acct}"
        node_idx[acct] = idx
        
        out_degree = G.out_degree(node_name)
        in_degree = G.in_degree(node_name)
        total_sent = sum(d.get("amount", 0.0) for _, _, d in G.out_edges(node_name, data=True))
        total_recv = sum(d.get("amount", 0.0) for _, _, d in G.in_edges(node_name, data=True))
        pass_through_rate = min(total_sent / (total_recv + 1e-5), 1.0)
        fan_out_ratio = out_degree / (in_degree + 1.0)
        
        recipients = [v for _, v in G.out_edges(node_name)]
        if recipients:
            counts = {}
            for r in recipients:
                counts[r] = counts.get(r, 0) + 1
            total_edges = len(recipients)
            entropy = -sum((c / total_edges) * np.log(c / total_edges) for c in counts.values())
        else:
            entropy = 0.0
        share_of_total_flow = total_sent / (total_sent + total_recv + 1e-5)
        
        pr = pagerank.get(node_name, 0.0) * 100
        deg = degree_cent.get(node_name, 0.0)
        bw = betweenness.get(node_name, 0.0)
        
        feats = [
            out_degree, in_degree, total_sent / 100000, total_recv / 100000,
            pass_through_rate, fan_out_ratio, entropy, share_of_total_flow,
            pr, deg, bw
        ]
        
        X_gnn.append(feats)
        y_gnn.append(labels.get(acct, 0)) # Default to 0 if not explicitly labeled

    # Build custom DiGraph with simple node ids
    G_simple = nx.DiGraph()
    for u, v, d in G.edges(data=True):
        u_id = u.split(":")[-1]
        v_id = v.split(":")[-1]
        G_simple.add_edge(u_id, v_id, amount=d.get("amount", 1.0), timestamp=d.get("timestamp", ""))

    feedback_graphs.append((G_simple, X_gnn, y_gnn))
    
    gnn = get_gnn_scorer()
    gnn.retrain(feedback_graphs)
    print("[SUCCESS] GNN weights updated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MuleNet ML Training Utility")
    parser.add_argument("--synthetic", action="store_true", help="Force retrain models on synthetic generator data")
    parser.add_argument("--csv", type=str, help="Train XGBoost model on custom features CSV file")
    parser.add_argument("--network-edges", type=str, help="CSV containing transaction edges (sender, receiver, amount, timestamp)")
    parser.add_argument("--network-labels", type=str, help="CSV containing account labels (account_id, label)")
    
    args = parser.parse_args()
    
    if args.synthetic:
        run_synthetic_training()
    elif args.csv:
        train_xgboost_from_csv(args.csv)
    elif args.network_edges and args.network_labels:
        train_from_network_csv(args.network_edges, args.network_labels)
    else:
        parser.print_help()
