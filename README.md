# MuleNet: Real-Time AI & Graph-Native Money Mule Detection

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Affiliation](https://img.shields.io/badge/Team-NoString-blueviolet.svg)](#-license--affiliation)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.1+-6DB33F.svg?logo=springboot)](https://spring.io/projects/spring-boot)
[![React](https://img.shields.io/badge/React-19.0+-61DAFB.svg?logo=react)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker)](https://www.docker.com)

> **MuleNet** is an enterprise-grade, graph-native real-time fraud decisioning platform engineered to detect and dismantle organized money mule networks (smurfing, multi-hop layering, pass-through mules, and coordinated syndicates) in milliseconds before illicit cash-outs occur.

---

## 🏗️ Architecture Overview

MuleNet combines a distributed, event-driven streaming pipeline with a dual-path Machine Learning inference engine:

```mermaid
graph TD
    %% Entities
    Sim[Transaction Ingestion Stream / Simulator]
    Kafka[Kafka Broker (upi.transactions)]
    Backend[Spring Boot Backend Engine]
    ML[FastAPI ML Inference Engine]
    Frontend[React Cyber-Fintech UI]
    
    %% Databases & Security
    DB_PG[(PostgreSQL - Audits/Cases)]
    DB_REDIS[(Redis - Feature Cache & Celery)]
    Keycloak[Keycloak OIDC SSO]

    %% Flow
    Sim -->|Ingests UPI & IMPS Transactions| Kafka
    Kafka -->|Consumes stream| Backend
    Backend -->|Dispatches Subgraph Inference| ML
    ML -->|Fast-Path XGBoost & Graph Neural Network| ML
    ML -->|Risk Scores, Topology & Velocity| Backend
    Backend -->|Autonomous Policy Engine (FREEZE / HOLD)| DB_PG
    Backend <-->|JWT / Role Validation| Keycloak
    Frontend <-->|Real-Time SSE Feed & REST APIs| Backend
```

### 🧠 Dual-Path AI Engine
1. **XGBoost Fast-Path (< 3 ms)**: Evaluates tabular transaction behavior, velocity surges, out-degree fan-out, and entropy.
2. **Graph Neural Network (GNN) Deep-Path (< 180 ms)**: Analyzes subgraph structural topology, cyclic routing, and multi-hop layering paths ($k \ge 3$).
3. **Unsupervised Anomaly Path**: Isolation Forest baseline detecting statistical drift in transaction volumes and account tenure.
4. **Autonomous Policy Engine**: Enforces automated actions (`FREEZE_IMMEDIATE`, `SOFT_HOLD`, `STEP_UP_MONITOR`) based on composite risk scores, I4C/NCRP intelligence uplift, and threshold configs.

---

## ⚡ Core Features

- **Mule Flow Explorer**: Interactive ReactFlow canvas visualizing money dispersal pathways with custom glowing HTML edge badges showing transfer amounts in Indian Rupees (`₹`), compact Lakh chips (`1.18 L`), and hop velocities.
- **Cash Flow Dynamics & Dossier**: Inflow vs. Outflow breakdown cards, real-time pass-through laundering velocity gauge (`% funds drained immediately`), and direct hop ledger.
- **Real-Time Stream Monitor**: Server-Sent Events (SSE) live feed delivering transaction events with instant ML scoring, risk badges, and auto-freeze controls.
- **External Watchlist Registry**: Real-time integration with I4C (Indian Cybercrime Coordination Centre), NCRP suspect registries, and blacklisted device fingerprints.
- **Cyber-Fintech Dark UI**: Built with accessible contrast, glassmorphism, animated glowing brand identity, and role-based access control (Supervisors, Investigators, Fraud Analysts).

---

## ⚙️ Tech Stack

| Domain | Technologies |
|---|---|
| **Backend Service** | Java 17, Spring Boot 3, Spring Security, Spring Kafka, Spring Data JPA, Hibernate |
| **Machine Learning** | Python 3.10+, FastAPI, PyTorch, PyTorch Geometric, XGBoost, Scikit-Learn, Celery |
| **Frontend UI** | React 19, Vite, ReactFlow, Lucide Icons, Material-UI, Recharts, Vanilla CSS Design System |
| **Event Streaming** | Confluent Kafka, Zookeeper |
| **Data & Cache** | PostgreSQL 15 (Relational Ledger), Redis 7 (Cache / Broker) |
| **Identity / Auth** | Keycloak 22 (OIDC / OAuth2 SSO) |
| **Containers** | Docker, Docker Compose |

---

## 🚀 Quick Start Guide

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/) (Recommended: 8 GB RAM allocated to Docker).
- *(Optional for local development)*: JDK 17+, Python 3.10+, Node.js 18+.

### 1. Environment Configuration
```bash
cp .env.example .env
```
*(Default test credentials are provided in `.env` for immediate local verification).*

### 2. Start Full Stack with Docker
Launch the unified stack in detached mode:
```bash
docker compose up -d
```
*Or on Windows, simply double-click:* **`run_all.bat`**

### 3. Access the Services
Once containers initialize:
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
  - **Username**: `investigator1`
  - **Password**: `password`
- **Backend API & Swagger**: [http://localhost:8080/api/health](http://localhost:8080/api/health)
- **ML Engine Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Keycloak Admin**: [http://localhost:8081](http://localhost:8081)

---

## 📊 Evaluation & Benchmarks

MuleNet models were evaluated on real PaySim financial transaction data and structured synthetic laundering graphs:

| Benchmark Metric | Model / Evaluator | Result |
|---|---|---|
| **ROC-AUC (FastPath XGBoost)** | PaySim Held-Out Split | **0.7567** |
| **PR-AUC (FastPath XGBoost)** | PaySim Held-Out Split | **0.0407** *(against 0.41% base rate)* |
| **Synthetic Topology ROC-AUC** | GNN + Centrality Features | **1.0000** |
| **Synthetic Topology PR-AUC** | GNN + Centrality Features | **1.0000** |
| **Scoring Latency / Transaction** | FastPath Pipeline | **0.0021 ms** |
| **Precision / Recall at Threshold** | Optimal F1 Operating Point | Precision: **0.9934** / Recall: **1.0000** |

### 💰 Economic Impact & Recovery
- **False-Positive Mitigation**: Automated hard freezes (`FREEZE_IMMEDIATE`) are strictly reserved for verified scores $\ge 70.0$. Borderline transactions route to `SOFT_HOLD` (preserving inbound liquidity while blocking outbound dissipation), saving institutions estimated thousands in operational overhead.
- **Demonstration Batch Recovery**: Across 3 multi-hop fraud networks totaling **₹6,43,000** in complaints, MuleNet auto-intercepted **₹3,20,000** before cash-out (**49.8% direct fund recovery rate**).

---

## 🧪 Testing

```bash
# Backend unit & integration tests
cd backend && ./mvnw clean test

# E2E Kafka streaming test
python scripts/kafka_e2e_test.py

# OAuth2 / Keycloak verification test
python scripts/oauth2_e2e_test.py

# ML training & validation suite
python ml_service/training/train_and_test.py
```

---

## 📄 License & Affiliation

MuleNet is released under the **MIT License**.

**Affiliated to the NoString team.**

See the [LICENSE](./LICENSE) file for complete terms and copyright details.
