def find_k(a, b, c, max_k=1000, epsilon=1):
    for x in range(1, max_k):
        for y in range(1, max_k - x + 1):
            lhs = a * x + b * y
            if abs(lhs - c) < epsilon:
                k = x + y
                return k
    return None  # No solution found within bounds

def process_list(a, b, c):
    k_list = []
    for i in range(0, len(a)-1):
        k = find_k(a[i], b[i], c[i])
        print(f"{i}: ====> {a[i], b[i], c[i]} =====> {k}")
        k_list.append(k)
    
    return pd.Series(k_list)

# Example usage:
import pandas as pd
import numpy as np

# Load your CSV
df = pd.read_csv('optimizer_result.csv') 

a = df["AVERAGE_WINN"]
b = df["AVERAGE_LOSS"]
c = df["TOTAL_PNL"]

df["NUM_OF_TRADE"] = process_list(a, b, c)
df.to_csv('optimizer_num_trade_added.csv', index=False)

