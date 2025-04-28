import pandas as pd
import numpy as np

# Load your CSV
df = pd.read_csv('optimizer_result.csv') 

# Handle division by zero and calculate Reward-to-Risk ratio
def compute_reward_to_risk(row):
    if row['AVERAGE_LOSS'] == 0:
        return 9999  # or np.inf if you prefer
    else:
        return row['AVERAGE_WINN'] / row['AVERAGE_LOSS']

# Add a new column for Reward-to-Risk
df['REWARD_TO_RISK'] = df.apply(compute_reward_to_risk, axis=1)

# Compute final score
df['SCORE'] = df['REWARD_TO_RISK'] * np.log1p(df['TOTAL_PNL'])

# Sort by Score descending
df_sorted = df.sort_values(by='SCORE', ascending=False)

# Output to a new CSV
df_sorted.to_csv('optimizer_sorted_result.csv', index=False)

# Find the best parameter set
best_row = df_sorted.loc[df['SCORE'].idxmax()]

print("Best Parameter Set:")
print(best_row)
