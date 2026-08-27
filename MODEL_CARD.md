# MuleNet Model Card

## Model Overview
MuleNet uses a hybrid ML architecture (FastPath + DeepPath + Anomaly Detection) to score accounts and transactions for likelihood of money mule behavior.

- **FastPath**: XGBoost / Gradient Boosting Classifier
- **DeepPath**: Graph Attention Network (GNN) Message-Passing Scorer
- **Anomaly Detection**: Isolation Forest

## Data Sources & Synthetic Generation
Because real financial transaction data containing verified mule networks is heavily protected by privacy laws, **these models are trained on a synthetic, procedurally-generated dataset** that closely mimics real-world mule typologies.

**Data Generation Profile (Synthetic):**
- **Fraud Rate (Class Imbalance)**: ~30% Positive (Mule), 70% Negative (Legitimate). 
- **Legitimate Profile**: Normal banking behavior. Poisson-distributed transaction rates. Standard income/expense cycles.
- **Mule Profile (Structuring/Smurfing)**:
  - High pass-through rate (receives funds and rapidly distributes them).
  - High fan-out ratio (sending to many disjoint accounts).
  - Specific counterparty entropy patterns indicating organized redistribution.

*(Note: In a live production environment, this synthetic data generator must be replaced with a pipeline pulling from an actual data warehouse containing historical flagged cases).*

## Model 1: FastPath (XGBoost)
- **Objective**: Rapidly evaluate tabular account-level features.
- **Features (8)**: `out_degree`, `in_degree`, `total_sent`, `total_recv`, `pass_through_rate`, `fan_out_ratio`, `counterparty_entropy`, `share_of_total_flow`.
- **Architecture**: 200 trees, max depth 5, learning rate 0.1.
- **Explainability**: Fully supports SHAP TreeExplainer for generating feature-level rationales (e.g., "Flagged because pass_through_rate > 95%").

## Model 2: DeepPath (GNN Scorer)
- **Objective**: Detect organized fraud rings that evade tabular thresholds by passing funds through multiple hops.
- **Features**: Inherits the 8 tabular features + 3 network centrality features (PageRank, Degree Centrality, Betweenness).
- **Architecture**: 2-layer Message Passing Network.
  - **Layer 1**: Neighbor aggregation weighted by edge transaction amounts and time-decay.
  - **Layer 2**: Self-attention weighting to produce a final 16-dimensional embedding, mapped to a probability via sigmoid.
- **Training**: Optimized via binary cross-entropy on synthetic sub-graphs.

## Model 3: Unsupervised Anomaly Detection
- **Objective**: Detect novel patterns (zero-day fraud) that the supervised models have never seen.
- **Architecture**: Isolation Forest (100 estimators, 10% contamination expectation).

## Limitations and Trade-offs
- **Synthetic Bias**: The models will perfectly detect the specific heuristics programmed into the synthetic generator (e.g., high pass-through). They may struggle with novel real-world typologies until retrained on real investigator feedback.
- **Latency vs. Graph Depth**: The GNN evaluates relationships up to 2 hops. Increasing depth improves detection of long money-laundering chains but increases inference latency exponentially.
- **Class Imbalance**: The synthetic dataset uses a 30% fraud rate for training stability. Real-world fraud rates are often <0.1%, meaning the raw output probabilities must be carefully thresholded (see `METRICS_REPORT.md` for the false-positive cost analysis).
