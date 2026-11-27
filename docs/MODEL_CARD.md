# Model Card: Research Candidates

## Intended Use

Offline fraud-model evaluation and simulated investigator workflow research.
Not for autonomous bank freezes, denial of service to customers or regulatory
filings. Scores are task-specific estimates, not determinations of criminal intent.

## Data and Protocol

AMLworld, PaySim and the local typology generator are simulated. Dataset versions,
licenses and hashes are recorded under reports; raw inputs remain local. Shared
features observe only events at or before query time. Account labels concern a
separate future interval. Temporal splits are purged; entity splits isolate whole
connected components. PaySim is a separate transaction task with pre-transfer
features and an explicitly separate post-transfer diagnostic.

## Models and Evidence

XGBoost uses validation early stopping, isotonic calibration and validation-only
operating thresholds. The GNN uses actual edge-aware message passing and neighbor
sampling. Isolation Forest is an unsupervised continuous signal, not a calibrated
fraud probability. Stacking uses validation out-of-fold predictions. Manifest and
schema checks precede parsing; integrity does not establish publisher identity.

Measured evidence is in [metrics](../reports/metrics.json),
[ablation](../reports/ablation.json), [typology](../reports/typology.json),
[adversarial](../reports/adversarial.json) and
[calibration](../reports/calibration.json). The generated README summarizes it.
Full-network AMLworld remains unmeasured. The recorded simulator operating point
misses positive cases in held-out evaluation. The GNN has not earned the default
path in these runs. Cohort feasibility diagnostics are not model performance.

## Failure Modes and Harm

Simulation mismatch, coarse validation FPR resolution, delayed relay, amount
splitting, merchant camouflage and incomplete histories can undermine detection.
Row-bootstrap intervals ignore account/ring dependence. Reusing validation for
calibration and threshold selection can overfit. SHAP explains model output,
not intent; observed evidence paths are not causal GNN explanations.

A false hold can interrupt essential payments, damage reputations and burden
investigators. Cost parameters are assumptions, not measured losses or recovery.
SOFT_HOLD is an internal bounded review state with release/appeal workflows, not
a bank action. Feedback needs independent review and quality controls; previous
model decisions are not ground truth. No live recovery or bank effectiveness has
been measured. Independent fairness and customer-impact studies remain absent.

## Deployment Limits

Drift baselines are hash-verified samples of TRAIN feature rows and fitted-model
scores, not test rows or the first live requests. Tenant-isolated feature/score
PSI/KS monitors have bounded, expiring windows and explicit readiness. Their
review thresholds are heuristics; neither multiple-testing control nor a live
false-drift-alarm rate is established. A constructed replay/shift probe verifies
behavior, not bank performance. Monitoring never changes scores, thresholds,
labels, holds or registry promotion automatically. Old bundles without baseline
evidence are incompatible with the new serving contract and must be retrained.

Security scans retain unresolved findings. Production approval, external
validation, publisher attestation and operating-organization sign-off are absent.
