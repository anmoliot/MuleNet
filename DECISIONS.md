# Implementation Decisions & Assumptions

## Task 1: OAuth2 / Keycloak
- **Keycloak Realm**: We generated a minimal realm `mule-realm` and a client `mulenet-app` locally in `KeycloakRealm.json` to bootstrap Keycloak automatically via `docker-compose`. This avoids manual configuration but can be easily substituted by modifying the JSON.
- **JWT Fallback**: We're relying on Spring Security configuration conditional on `app.security.oauth2.enabled` property to enable OAuth2 Resource Server.

## Task 6: Secrets Management
- All hardcoded credentials from `docker-compose.yml` have been externalized to `.env`.
- An `.env.example` has been created.
- `docker-compose.yml` now utilizes variable interpolation for secrets.

## Deployment Assumptions (Buildathon Readiness)
- **Deployment Platform**: No live cloud credentials (AWS, GCP, Render) were available in the autonomous environment. Therefore, no live URL was fabricated. 
- **Local Fallback**: The primary deployment vehicle verified for evaluators is the local `docker-compose.yml`, which brings up the entire 10-container stack end-to-end.
- **Render.yaml**: A `render.yaml` file was provided as a one-command deploy path for PaaS environments, but infrastructure like Kafka and Neo4j require persistent storage and should ideally be connected to managed instances (e.g. Confluent Cloud) for a true production deployment.

## Machine Learning Assumptions
- **Synthetic Data**: Because real mule transaction data is private, the ML models (`FastPath` XGBoost and `DeepPath` GNN) were trained on procedurally generated synthetic graph data. 
- **Fraud Rate**: The synthetic generator uses a 30% fraud rate for training stability (class balance). In production, this would be highly imbalanced (<0.1%).
- **Model Storage**: Trained model artifacts (`.pkl` files) are saved natively in the `trained_models/` directory for fast startup.
- **Metrics Modeling**: The false-positive cost analysis assumes $50 per false positive (friction) and $500 per false negative (fraud loss). These are placeholders to demonstrate the cost-optimization capabilities of the platform.
