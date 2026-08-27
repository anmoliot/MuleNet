import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import precision_recall_curve, roc_curve, auc, confusion_matrix, f1_score

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml_models import FastPathModel, _generate_training_data

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'reports', 'metrics'))
os.makedirs(REPORTS_DIR, exist_ok=True)

def main():
    print("=== Generating ML Metrics ===")
    model = FastPathModel()
    
    # Generate a held-out test set (seed 99 for separation from training)
    print("Generating synthetic test set (seed 99)...")
    X_test, y_test = _generate_training_data(n_samples=2000, seed=99)
    
    X_scaled = model.scaler.transform(X_test)
    probs = model.model.predict_proba(X_scaled)[:, 1]
    
    # Calculate PR and ROC curves
    precision, recall, pr_thresholds = precision_recall_curve(y_test, probs)
    fpr, tpr, roc_thresholds = roc_curve(y_test, probs)
    
    roc_auc = auc(fpr, tpr)
    pr_auc = auc(recall, precision)
    
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"PR-AUC: {pr_auc:.4f}")
    
    # Plot ROC
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC)')
    plt.legend(loc="lower right")
    plt.savefig(os.path.join(REPORTS_DIR, 'roc_curve.png'))
    plt.close()
    
    # Plot PR
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, color='blue', lw=2, label=f'PR curve (area = {pr_auc:.3f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend(loc="lower left")
    plt.savefig(os.path.join(REPORTS_DIR, 'pr_curve.png'))
    plt.close()
    
    # Cost Trade-off Modeling
    # Assume: 
    # False Positive = $50 (customer friction, manual investigator review cost)
    # False Negative = $500 (average fraud loss)
    # True Positive / True Negative cost = $0
    
    COST_FP = 50
    COST_FN = 500
    
    thresholds = np.linspace(0.01, 0.99, 99)
    costs = []
    f1_scores = []
    
    for t in thresholds:
        preds = (probs >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_test, preds).ravel()
        cost = (fp * COST_FP) + (fn * COST_FN)
        costs.append(cost)
        f1_scores.append(f1_score(y_test, preds))
        
    optimal_cost_idx = np.argmin(costs)
    optimal_f1_idx = np.argmax(f1_scores)
    
    t_opt_cost = thresholds[optimal_cost_idx]
    t_opt_f1 = thresholds[optimal_f1_idx]
    
    print(f"Optimal Threshold (Min Cost): {t_opt_cost:.2f} (Total Cost: ${costs[optimal_cost_idx]})")
    print(f"Optimal Threshold (Max F1): {t_opt_f1:.2f} (F1: {f1_scores[optimal_f1_idx]:.4f})")
    
    # Plot Cost vs Threshold
    plt.figure(figsize=(8, 6))
    plt.plot(thresholds, costs, color='red', lw=2, label='Expected Cost')
    plt.axvline(t_opt_cost, color='black', linestyle='--', label=f'Min Cost Threshold ({t_opt_cost:.2f})')
    plt.axvline(t_opt_f1, color='blue', linestyle='-.', label=f'Max F1 Threshold ({t_opt_f1:.2f})')
    plt.xlabel('Decision Threshold')
    plt.ylabel('Total Expected Cost ($)')
    plt.title('False Positive vs. False Negative Cost Trade-off')
    plt.legend()
    plt.savefig(os.path.join(REPORTS_DIR, 'cost_curve.png'))
    plt.close()
    
    # Output final metrics for report
    print("\n--- Final Metrics to copy into METRICS_REPORT.md ---")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"PR-AUC: {pr_auc:.4f}")
    print(f"F1 (at {t_opt_f1:.2f}): {f1_scores[optimal_f1_idx]:.4f}")
    
    preds_opt = (probs >= t_opt_cost).astype(int)
    cm = confusion_matrix(y_test, preds_opt)
    print("\nConfusion Matrix at Minimum Cost Threshold:")
    print(cm)
    print("\nDone. Charts saved to reports/metrics/.")

if __name__ == "__main__":
    main()
