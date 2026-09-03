import pandas as pd
import numpy as np
import scipy.stats
import math
import os

def prepare_paysim():
    input_file = r"C:\Users\Anmol\Downloads\PS_20174392719_1491204439457_log.csv\PS_20174392719_1491204439457_log.csv"
    output_file = r"C:\Users\Anmol\OneDrive\Desktop\MuleNet\processed_paysim.csv"
    
    print(f"Loading PaySim data from: {input_file}")
    # Read only a chunk or the whole dataset? It's 6 million rows, might take a bit but pandas can handle it.
    # To keep it quick, we can process a subset or the whole thing. Let's do the whole thing.
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} transactions.")
    
    print("Aggregating account-level features...")
    
    # 1. Sent metrics (Group by nameOrig)
    sent_stats = df.groupby('nameOrig').agg(
        total_sent=('amount', 'sum'),
        out_degree=('nameDest', 'nunique'),
        tx_count_out=('nameDest', 'count')
    )
    
    # Counterparty entropy for sent (how spread out are the transactions to different destinations)
    # We can approximate entropy by looking at value counts, but doing it grouped is slow.
    # A fast proxy: out_degree / tx_count_out (1.0 means perfectly uniform, lower means concentrated)
    # To map this roughly to entropy, we can use log(out_degree) * (out_degree / tx_count_out)
    sent_stats['entropy_out'] = np.log1p(sent_stats['out_degree']) * (sent_stats['out_degree'] / sent_stats['tx_count_out'])
    
    # 2. Received metrics (Group by nameDest)
    recv_stats = df.groupby('nameDest').agg(
        total_recv=('amount', 'sum'),
        in_degree=('nameOrig', 'nunique'),
        tx_count_in=('nameOrig', 'count')
    )
    recv_stats['entropy_in'] = np.log1p(recv_stats['in_degree']) * (recv_stats['in_degree'] / recv_stats['tx_count_in'])
    
    # 3. Fraud Labels
    # In PaySim, fraudulent transfers go from hijacked accounts (nameOrig) to mule accounts (nameDest)
    fraud_df = df[df['isFraud'] == 1]
    mule_accounts = set(fraud_df['nameDest'].unique())
    compromised_accounts = set(fraud_df['nameOrig'].unique())
    fraud_accounts = mule_accounts.union(compromised_accounts)
    
    # Combine sent and recv
    accounts = pd.DataFrame(index=sent_stats.index.union(recv_stats.index))
    accounts = accounts.join(sent_stats).join(recv_stats).fillna(0)
    
    # Calculate derived features required by MuleNet:
    # "out_degree", "in_degree", "total_sent", "total_recv", "pass_through_rate", "fan_out_ratio", "counterparty_entropy", "share_of_total_flow"
    
    accounts['pass_through_rate'] = np.where(
        accounts['total_recv'] > 0,
        np.clip(accounts['total_sent'] / accounts['total_recv'], 0, 1.0),
        0.0
    )
    
    accounts['fan_out_ratio'] = accounts['out_degree'] / (accounts['in_degree'] + 1)
    
    # Average the entropy proxy
    accounts['counterparty_entropy'] = (accounts['entropy_out'] + accounts['entropy_in']) / 2.0
    
    # Share of total flow (proxy)
    total_flow_global = df['amount'].sum()
    accounts['share_of_total_flow'] = (accounts['total_sent'] + accounts['total_recv']) / total_flow_global
    
    # Labels
    accounts['label'] = accounts.index.isin(fraud_accounts).astype(int)
    
    # Ensure correct columns
    final_cols = [
        "out_degree", "in_degree", "total_sent", "total_recv", 
        "pass_through_rate", "fan_out_ratio", "counterparty_entropy", 
        "share_of_total_flow", "label"
    ]
    
    final_df = accounts[final_cols]
    
    print(f"Processed {len(final_df)} unique accounts. Found {final_df['label'].sum()} fraudulent/mule accounts.")
    
    print(f"Saving to {output_file}...")
    final_df.to_csv(output_file, index=False)
    print("Done!")

if __name__ == "__main__":
    prepare_paysim()
