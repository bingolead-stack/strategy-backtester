import pandas as pd
import numpy as np

# Load your CSV
df = pd.read_csv('long_result/optimizer_result.csv') 

def target_function(win_rate, total_pnl, reward_to_risk, num_of_trade,
                    w_win=0, w_pnl=1, w_rr=0, w_trades=0):
    # Normalize
    win_rate_norm = min(win_rate / 100, 1.0)
    pnl_norm = total_pnl / 301475
    rr_norm = min(reward_to_risk / 13.8, 1.0)
    trades_norm = min(num_of_trade / 1000, 1.0)

    # Optional: apply penalty if too few trades
    if num_of_trade < 30:
        penalty = 0.5
    else:
        penalty = 1

    # Weighted sum with penalty
    score = (w_win * win_rate_norm +
             w_pnl * pnl_norm +
             w_rr * rr_norm +
             w_trades * trades_norm) * penalty

    return score

# Compute final score
df["SCORE"] = df.apply(
    lambda row: target_function(
        row["WIN_RATE"],
        row["TOTAL_PNL"],
        row["REWARD_TO_RISK"],
        row["NUM_OF_TRADE"]
    ),
    axis=1
)

# # Sort by Score descending
df_sorted = df.sort_values(by='SCORE', ascending=False)

# Output to a new CSV
df_sorted.to_csv('long_result/optimizer_final_result.csv', index=False)

# Find the best parameter set
best_row = df_sorted.loc[df_sorted['SCORE'].idxmax()]

print("Best Parameter Set:")
print(best_row)
