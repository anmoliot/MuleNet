# MuleNet Metrics & False-Positive Cost Trade-off

This report details the quantitative performance of the MuleNet multi-layered detection models across both large-scale real-world benchmark data (PaySim, 3.34M accounts) and high-fidelity held-out synthetic mule network topologies.

---

## 1. Large-Scale Benchmark: PaySim Dataset (3.34 Million Accounts)
Trained on account-level tabular features with a strictly separated temporal/account-level train-test split to prevent data leakage:

- **Total Accounts Analyzed**: 3,345,842 accounts
- **Training Accounts**: 3,094,654 (15,336 verified mule accounts)
- **Held-Out Test Accounts**: 251,188 (1,051 verified mule accounts, 0.41% base rate)
- **ROC-AUC (XGBoost FastPath)**: **0.7567** (robust discriminatory power on extreme class imbalance)
- **PR-AUC (XGBoost FastPath)**: **0.0407** (10x uplift over 0.0041 random baseline)
- **Best Decision Threshold (F1)**: **0.90**
- **Input Features (8)**: `out_degree`, `in_degree`, `log_total_sent`, `log_total_recv`, `receive_send_ratio`, `counterparty_ratio`, `entropy_normalized`, `flow_normalized`
- **Total Ingestion Volume Analyzed**: ₹824,551,434,143.24 (₹824.55 Billion)

---

## 2. Multi-Hop Graph & Topology Benchmark (Held-Out Test Set)
Evaluated on complex multi-hop structuring, smurfing, and funnel network topologies:

- **Held-Out Accounts Tested**: 3,000 accounts (900 mules, 2,100 legitimate)
- **ROC-AUC (FastPath XGBoost)**: **1.0000**
- **PR-AUC (FastPath XGBoost)**: **1.0000**
- **ROC-AUC (Isolation Forest Anomaly)**: **0.6074**
- **Average Inference Latency**: **0.0021 ms** per transaction
- **Optimal Decision Threshold (F1)**: **0.30** (Precision: 0.9934, Recall: 1.0000, F1: 0.9967)

---

## 3. False-Positive vs. False-Negative Cost Optimization

In banking and UPI payment security, optimizing strictly for raw accuracy is fatal because the financial impacts of False Positives (FP) and False Negatives (FN) are highly asymmetrical:

### Economic Cost Assumptions
- **Cost of a False Positive (FP): ₹1,000** 
  *Represents customer friction, call center support tickets, and investigator manual review hours.*
- **Cost of a False Negative (FN): ₹50,000+** 
  *Represents the direct unrecoverable fraud loss when money exits the banking rail via ATM/crypto.*

### Cost-Optimal Threshold Policy
- A naïve 3% FP rate on 10,000 alerts/day costs financial institutions **≈ ₹300,000 / day**.
- **MuleNet Solution**:
  1. `FREEZE_IMMEDIATE` is auto-executed only on high-confidence alerts **≥ 70.0** (or composite score ≥ 0.90).
  2. Intermediate scores (35–69) route to `SOFT_HOLD` (blocking outward disbursement while permitting inward deposits) and `STEP_UP_MONITOR`.
  3. GNN message-passing and network topology features re-rank second-hop concentration accounts before any irrevocable account freeze.

---

## 4. Money-Saved & Fund Recovery Across Batch (Demo Seeded Cases)

| Case ID | Complaint Amount | Primary Flagged Mule | Frozen At-Risk | Est. Recoverable | Status |
|---|---|---|---|---|---|
| **CASE-1001** | ₹245,000 | `AC-DRAIN-8821` (Score: 95.2) | ₹198,000 | ₹95,000 | INVESTIGATING |
| **CASE-1002** | ₹88,000 | `AC-CASHCAP-44` (Score: 82.0) | ₹72,500 | ₹45,000 | OPEN |
| **CASE-1003** | ₹310,000 | `AC-DRAIN-8821` (Score: 88.4) | ₹274,000 | ₹180,000 | FROZEN |
| **Batch Total** | **₹643,000** | **3 Mule Accounts** | **₹544,500** | **₹320,000** | **49.8% Recovery** |

*Across the batch, ₹544,500 (84.7%) of fraudulent outflow was intercepted, with ₹320,000 (49.8%) secured for immediate victim restitution before final cash-out.*

