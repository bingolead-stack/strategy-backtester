import pandas as pd
import numpy as np

# Load your CSV
df = pd.read_csv('optimizer_result_add_num_of_trade.csv') 

# Handle division by zero and calculate Reward-to-Risk ratio
def compute_reward_to_risk(row):
    if (row['NUM_OF_TRADE'] < 10): # Skip low trade numbers
        return 0 
    return row['AVERAGE_WINN'] / max(1, abs(row['AVERAGE_LOSS']))

# Add a new column for Reward-to-Risk
df['REWARD_TO_RISK'] = df.apply(compute_reward_to_risk, axis=1)

# Output to a new CSV
df.to_csv('optimizer_result_add_reward_to_risk.csv', index=False)
