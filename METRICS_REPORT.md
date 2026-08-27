# MuleNet Metrics & False-Positive Cost Trade-off

This report details the quantitative performance of the MuleNet FastPath (XGBoost) model on a held-out test set (N=2000) generated using the platform's synthetic fraud topologies.

## Core Performance Metrics
Because the synthetic data generator utilizes specific typologies for money mules (e.g., highly elevated pass-through rates and fan-out ratios), the FastPath model achieves perfect linear separation on the synthetic test set. 

- **ROC-AUC**: 1.0000
- **PR-AUC**: 1.0000
- **Max F1 Score**: 1.0000 (at threshold 0.31)

*(Note: In a production environment with real-world noise and overlapping distributions, these metrics will drop. The system architecture is built to automatically log these metrics to MLflow for continuous monitoring against model drift).*

## False-Positive vs. False-Negative Cost Trade-off

In banking fraud, optimizing strictly for accuracy or F1 score is often sub-optimal because the financial impacts of False Positives (FP) and False Negatives (FN) are highly asymmetrical.

### Cost Assumptions
- **Cost of a False Positive (FP): $50** 
  *Represents the cost of customer friction (e.g., a blocked legitimate transfer requiring a support call) and the manual investigator time required to resolve the case.*
- **Cost of a False Negative (FN): $500** 
  *Represents the average direct financial loss when a fraudulent transaction successfully cashes out.*

### Threshold Optimization
By sweeping the decision threshold from `0.01` to `0.99`, MuleNet dynamically evaluates the total expected cost.

Because the data is perfectly separable, the minimum expected cost ($0) and the maximum F1 score both align at **Threshold = 0.31**. 

### Confusion Matrix (At optimal threshold 0.31)
```
[[1400    0]   # True Negatives (1400) | False Positives (0)
 [   0  600]]  # False Negatives (0)   | True Positives (600)
```

## Generated Charts
The ML metrics pipeline automatically outputs visualizing charts to the `reports/metrics/` directory:
- `roc_curve.png`: Receiver Operating Characteristic.
- `pr_curve.png`: Precision-Recall Curve.
- `cost_curve.png`: Cost vs. Threshold sweep.
