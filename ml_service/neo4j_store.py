import os
from neo4j import GraphDatabase

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "passwordpassword")


class Neo4jGraphStore:
    """
    Neo4j connection wrapper for MuleNet Graph Ingestion & Querying.
    Allows real graph-native database scaling (Gap 2 fallback).
    """

    def __init__(self):
        self.driver = None
        self.enabled = False
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            # Test connection
            self.driver.verify_connectivity()
            self.enabled = True
            print(f"[Neo4j] Connected successfully to graph store at {NEO4J_URI}")
        except Exception as e:
            print(f"[Neo4j] Driver initialization failed: {e}. Graph queries will default to NetworkX.")

    def close(self):
        if self.driver:
            self.driver.close()

    def add_account(self, tx, account_id, is_merchant=False):
        label = "Merchant" if is_merchant else "Account"
        query = f"MERGE (a:Account {{id: $account_id}}) ON CREATE SET a.label = $label, a.node_type = $node_type"
        tx.run(query, account_id=account_id, label=label, node_type="merchant" if is_merchant else "account")

    def add_transaction(self, sender, receiver, amount, timestamp, utr, sender_merchant=False, receiver_merchant=False):
        if not self.enabled:
            return

        def _work(tx):
            # Merge nodes
            self.add_account(tx, sender, sender_merchant)
            self.add_account(tx, receiver, receiver_merchant)
            # Create transaction edge
            query = """
            MATCH (s:Account {id: $sender}), (r:Account {id: $receiver})
            CREATE (s)-[t:SENT_TO {amount: $amount, timestamp: $timestamp, utr: $utr, edge_type: 'sent_to'}]->(r)
            """
            tx.run(query, sender=sender, receiver=receiver, amount=amount, timestamp=timestamp, utr=utr)

        with self.driver.session() as session:
            session.execute_write(_work)

    def add_device_link(self, account_id, device_id):
        if not self.enabled:
            return

        def _work(tx):
            tx.run("MERGE (a:Account {id: $account_id})", account_id=account_id)
            tx.run("MERGE (d:Device {id: $device_id}) ON CREATE SET d.node_type = 'device'", device_id=device_id)
            query = """
            MATCH (a:Account {id: $account_id}), (d:Device {id: $device_id})
            MERGE (a)-[r:USES_DEVICE {edge_type: 'uses_device'}]->(d)
            """
            tx.run(query, account_id=account_id, device_id=device_id)

        with self.driver.session() as session:
            session.execute_write(_work)

    def add_complaint(self, complaint_id, amount, utr, timestamp, first_beneficiary):
        if not self.enabled:
            return

        def _work(tx):
            tx.run("""
            MERGE (c:Complaint {id: $complaint_id}) 
            ON CREATE SET c.amount = $amount, c.utr = $utr, c.timestamp = $timestamp, c.node_type = 'complaint'
            """, complaint_id=complaint_id, amount=amount, utr=utr, timestamp=timestamp)
            
            self.add_account(tx, first_beneficiary, False)
            
            tx.run("""
            MATCH (c:Complaint {id: $complaint_id}), (a:Account {id: $beneficiary})
            MERGE (c)-[r:LINKED_TO_CASE {edge_type: 'linked_to_case'}]->(a)
            """, complaint_id=complaint_id, beneficiary=first_beneficiary)

        with self.driver.session() as session:
            session.execute_write(_work)

    def get_neighborhood(self, account_id, hops=2):
        """
        Query Neo4j for nodes and edges within N hops of target account_id.
        Returns format identical to GLOBAL_GRAPH queries for frontend compatibility.
        """
        if not self.enabled:
            return None

        query = """
        MATCH (a:Account {id: $account_id})
        MATCH path = (a)-[r:SENT_TO|USES_DEVICE|LINKED_TO_CASE*1..2]-(n)
        UNWIND nodes(path) AS node
        UNWIND relationships(path) AS rel
        RETURN collect(distinct node) AS nodes, collect(distinct rel) AS rels
        """

        nodes_list = []
        edges_list = []

        try:
            with self.driver.session() as session:
                result = session.run(query, account_id=account_id)
                record = result.single()
                if not record:
                    return {"nodes": [], "edges": []}

                nodes = record["nodes"]
                rels = record["rels"]

                # Process nodes
                for node in nodes:
                    n_id = node["id"]
                    labels = list(node.labels)
                    n_type = node.get("node_type", "account")
                    nodes_list.append({
                        "id": n_id,
                        "type": n_type,
                        "details": dict(node)
                    })

                # Process edges
                for rel in rels:
                    u = rel.nodes[0]["id"]
                    v = rel.nodes[1]["id"]
                    edge_type = rel.get("edge_type", "sent_to")

                    if edge_type == "sent_to":
                        edges_list.append({
                            "from": u,
                            "to": v,
                            "amount": rel.get("amount", 0.0),
                            "timestamp": rel.get("timestamp", ""),
                            "utr": rel.get("utr", "")
                        })
                    elif edge_type == "uses_device":
                        edges_list.append({
                            "from": u,
                            "to": v,
                            "type": "device_link"
                        })
                    elif edge_type == "linked_to_case":
                        edges_list.append({
                            "from": u,
                            "to": v,
                            "type": "case_link"
                        })

                return {
                    "status": "success",
                    "account_id": account_id,
                    "nodes": nodes_list,
                    "edges": edges_list
                }
        except Exception as e:
            print(f"[Neo4j] Error fetching neighborhood: {e}")
            return None


# Singleton Instance
_neo4j_graph: Neo4jGraphStore = None

def get_neo4j_graph() -> Neo4jGraphStore:
    global _neo4j_graph
    if _neo4j_graph is None:
        _neo4j_graph = Neo4jGraphStore()
    return _neo4j_graph
