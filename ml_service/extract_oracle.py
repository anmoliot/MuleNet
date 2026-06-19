#!/usr/bin/env python
"""
extract_oracle.py — Extracts transaction and label data from Oracle DB and trains models.
"""

import os
import csv
import sys
import argparse
from pathlib import Path

try:
    import oracledb
except ImportError:
    print("[Error] 'oracledb' package is not installed. Please run: pip install oracledb")
    sys.exit(1)

def extract_and_train(args):
    print("=== Connecting to Oracle Database ===")
    print(f"DSN: {args.host}:{args.port}/{args.sid_or_service}")
    print(f"User: {args.user}")

    # Establish connection
    try:
        # Check if service name or SID is used
        if args.is_service_name:
            connection = oracledb.connect(
                user=args.user,
                password=args.password,
                host=args.host,
                port=args.port,
                service_name=args.sid_or_service
            )
        else:
            connection = oracledb.connect(
                user=args.user,
                password=args.password,
                host=args.host,
                port=args.port,
                sid=args.sid_or_service
            )
        print("[SUCCESS] Connected to Oracle Database successfully.")
    except Exception as e:
        print(f"[Error] Failed to connect to Oracle: {e}")
        print("\nPlease make sure:")
        print(" 1. The Oracle XE Service is running (net start OracleServiceXE)")
        print(" 2. Your credentials, host, port, and SID/service name are correct.")
        sys.exit(1)

    cursor = connection.cursor()

    # 1. Extract Edges
    edges_path = Path("oracle_edges.csv")
    print(f"\nExtracting transaction edges from table '{args.tx_table}'...")
    try:
        # Select standard columns
        query = f"SELECT sender_account, receiver_account, amount, timestamp FROM {args.tx_table}"
        cursor.execute(query)
        
        with open(edges_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sender_account", "receiver_account", "amount", "timestamp"])
            row_count = 0
            for row in cursor:
                writer.writerow(row)
                row_count += 1
        print(f"[SUCCESS] Extracted {row_count} transaction edges to '{edges_path}'.")
    except Exception as e:
        print(f"[Error] Failed to query transactions table: {e}")
        connection.close()
        sys.exit(1)

    # 2. Extract Labels
    labels_path = Path("oracle_labels.csv")
    print(f"\nExtracting account labels from table '{args.labels_table}'...")
    try:
        query = f"SELECT account_id, label FROM {args.labels_table}"
        cursor.execute(query)
        
        with open(labels_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["account_id", "label"])
            row_count = 0
            for row in cursor:
                writer.writerow(row)
                row_count += 1
        print(f"[SUCCESS] Extracted {row_count} account labels to '{labels_path}'.")
    except Exception as e:
        print(f"[Error] Failed to query labels table: {e}")
        connection.close()
        sys.exit(1)

    # Clean up DB resources
    cursor.close()
    connection.close()

    # 3. Execute Training
    print("\n=== Running MuleNet ML Model Training Pipeline ===")
    train_script = Path(__file__).parent / "train.py"
    
    import subprocess
    cmd = [
        sys.executable,
        str(train_script),
        "--network-edges", str(edges_path),
        "--network-labels", str(labels_path)
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("\n[SUCCESS] Model training from Oracle data completed successfully!")
    else:
        print(f"\n[Error] Model training script exited with code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract from Oracle credit card database and train models")
    parser.add_argument("--host", default="localhost", help="Oracle DB host")
    parser.add_argument("--port", type=int, default=1521, help="Oracle DB port")
    parser.add_argument("--sid-or-service", default="XE", help="Oracle SID or Service Name")
    parser.add_argument("--is-service-name", action="store_true", help="Connect using service_name instead of SID")
    parser.add_argument("--user", required=True, help="Oracle username")
    parser.add_argument("--password", required=True, help="Oracle password")
    parser.add_argument("--tx-table", default="credit_card_transactions", help="Table name for transaction edges")
    parser.add_argument("--labels-table", default="account_labels", help="Table name for account labels")
    
    args = parser.parse_args()
    extract_and_train(args)
