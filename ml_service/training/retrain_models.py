import logging
import os
import sys

# Ensure repository root is on PYTHONPATH for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from train_xgboost import main as train_xgboost
from train_gnn import main as train_gnn
from train_isolation_forest import main as train_isolation_forest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    logging.info("=== Starting periodic model retraining ===")
    try:
        train_xgboost()
        logging.info("XGBoost retraining completed")
    except Exception as e:
        logging.error(f"XGBoost training failed: {e}")
    try:
        train_gnn()
        logging.info("GNN retraining completed")
    except Exception as e:
        logging.error(f"GNN training failed: {e}")
    try:
        train_isolation_forest()
        logging.info("IsolationForest retraining completed")
    except Exception as e:
        logging.error(f"IsolationForest training failed: {e}")
    logging.info("=== Periodic retraining finished ===")

if __name__ == "__main__":
    main()
