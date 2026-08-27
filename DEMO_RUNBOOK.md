# MuleNet Demo Runbook

This runbook provides the step-by-step instructions to execute a live 5-minute pitch demonstration of the MuleNet Fraud Detection Platform.

## Prerequisites
Ensure the environment is clean and all Docker images are built.
1. Clear old data: `docker-compose down -v`
2. Start the stack: `docker-compose up -d`
3. Wait ~60 seconds for Keycloak, Kafka, and the ML Service to initialize.
4. Have the React Dashboard open in a browser: `http://localhost:3000` (Login: `investigator1` / `password`).
5. Have a terminal open for executing the simulator.

---

## Part 1: The "Happy Path" Fraud Detection (1.5 minutes)
**Goal:** Show the simulator producing a high-risk transaction graph and the system catching it in real-time.

1. **Trigger the Simulator**
   In your terminal, run the E2E simulation script which produces a known fraud topology into Kafka:
   ```bash
   python scripts/kafka_e2e_test.py
   ```
2. **Watch the Dashboard**
   - Switch immediately to the React Dashboard.
   - You should see the live alert pop up on the streaming event feed.
   - Click into the alert to view the **Graph Explorer**.
3. **Talk Track**
   - Point out the complex fan-out topology (smurfing behavior).
   - Point out the FastPath XGBoost score and the DeepPath GNN score.
   - Show that the **Policy Engine** automatically escalated this to a `FREEZE_IMMEDIATE` state based on the high confidence score, intercepting the funds before cash-out.

---

## Part 2: Graceful Degradation & Resilience (1.5 minutes)
**Goal:** Demonstrate that the system is resilient to ML service outages via the retry queues (Celery/Spring Retry).

1. **Simulate a Service Outage**
   In your terminal, kill the ML service:
   ```bash
   docker stop mulenet-ml-service
   ```
2. **Trigger Another Event**
   Run the simulator again:
   ```bash
   python scripts/kafka_e2e_test.py
   ```
3. **Observe the Backend Behavior**
   - Show the backend logs (`docker logs mulenet-backend --tail 50`).
   - You will see Spring `@Retryable` attempting to reach the ML service 3 times, then falling back to an error state or queuing the analysis for later.
4. **Recover the Service**
   Start the ML service back up:
   ```bash
   docker start mulenet-ml-service
   ```
5. **Talk Track**
   - Explain how in a live payment rail, ML timeouts cannot drop transactions.
   - Explain how MuleNet queues and retries evaluations gracefully without silent failures.

---

## Part 3: Metrics & Governance (1 minute)
**Goal:** Show that the model performance is measurable and optimized for business outcomes.

1. **Show the Metrics Report**
   Open `METRICS_REPORT.md` (or the `reports/metrics` folder images).
2. **Talk Track**
   - Highlight the **Cost Trade-off Curve**.
   - Explain that instead of just optimizing for F1 score, MuleNet allows the business to set the decision threshold based on the actual dollar cost of a false positive (customer friction) versus a false negative (fraud loss).
   - Present the final PR-AUC and ROC-AUC numbers.
