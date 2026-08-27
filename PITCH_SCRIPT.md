# MuleNet 5-Minute Pitch Script

**Speaker**: [Your Name/Team Name]
**Duration**: 5 minutes
**Assets Needed**: Screen recording (or live screen share) showing the React Dashboard and a terminal. 

---

### [0:00 - 1:00] The Problem & The Solution
**Speaker**: 
"Hello everyone. Every year, billions of dollars are laundered through 'money mules'—networks of accounts used to layer and obscure the origin of illicit funds. Traditional fraud systems look at single transactions or tabular rules. They are blind to the *topology* of how money flows across the network. 

Enter MuleNet. MuleNet is a graph-native fraud decisioning platform. Instead of just looking at the size of a transaction, we ingest streaming data from Kafka, construct a real-time trust graph in Neo4j, and apply a hybrid machine learning approach. We use XGBoost for blazing-fast tabular scoring, and a Graph Neural Network—or GNN—to actually detect complex, multi-hop smurfing patterns. And critically, our Policy Engine intercepts the money *before* it cashes out."

---

### [1:00 - 2:30] Live Demo (Happy Path)
**Speaker**: 
"Let’s see it in action. On the screen, you see the MuleNet Investigator Dashboard. Behind the scenes, we have a live Kafka stream waiting for events. 
*(Action: Switch to terminal, run `python scripts/kafka_e2e_test.py`)*

I’m going to simulate a burst of transactions mimicking a classic fan-out mule typology. 
*(Action: Switch back to the dashboard immediately)*

Boom. Instantly, the backend consumes the stream, the ML service analyzes the graph, and an alert is pushed via WebSockets to our dashboard. If we look at this case, we see the FastPath and DeepPath models both flagged it with high confidence. Because the score crossed our critical threshold, the Policy Engine didn't just alert us—it issued a `FREEZE_IMMEDIATE` action. The funds are locked."

---

### [2:30 - 3:30] Graceful Degradation (The Real-World Test)
**Speaker**: 
"But we all know what happens in production. Services go down. If you're blocking real-time payment rails, you cannot afford to drop transactions just because an ML container restarted.

*(Action: Switch to terminal, type `docker stop mulenet-ml-service`)*
I’ve just killed our Machine Learning service. 

*(Action: Run the simulator script again)*
Watch what happens when another transaction hits Kafka. 
*(Action: Show backend logs)*
The backend attempts to reach the ML engine, detects the failure, and instead of crashing or dropping the payment, Spring Retry kicks in. It attempts three exponential backoffs. If the service stays down, it safely routes the transaction to a degraded fallback queue. 

*(Action: `docker start mulenet-ml-service`)*
As soon as the ML service recovers, the queue processes. We prioritize resilience over everything."

---

### [3:30 - 4:30] Measurable Results & Business Value
**Speaker**: 
"Finally, let’s talk about accuracy and business value. We trained our models on simulated topological signatures—yielding a perfect 1.0 ROC-AUC in our synthetic test set. But more importantly, MuleNet allows business leaders to model the **false-positive cost trade-off**. 

We know that a false positive costs us about $50 in customer friction, while a false negative costs $500 in actual fraud loss. By sweeping our decision thresholds against this asymmetric cost structure, MuleNet automatically identified that an operating threshold of 0.31 strictly minimizes our financial exposure, achieving a perfect F1 score on our test set. We aren't just optimizing for data science metrics; we are optimizing for the bottom line."

---

### [4:30 - 5:00] Conclusion
**Speaker**: 
"MuleNet combines stream processing, graph neural networks, and fault-tolerant architecture into a single, deployable package. It doesn’t just detect fraud—it dismantles the network. Thank you."
