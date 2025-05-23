from itertools import product
import json

from strategy.strategy import Strategy
from strategy.strategy_backtester import StrategyBacktester

import pandas as pd
import os

# Delete previous optimizer result if it exists
output_file = "short_result/optimizer_result.csv"
if os.path.exists(output_file):
    os.remove(output_file)
    print(f"Deleted existing file: {output_file}")

results = []
# === Load Config ===
with open("optimizer_config.json", "r") as f:
    optimizer_config = json.load(f)
    STATIC_LEVELS = optimizer_config.get("static_levels", [])
    param_grid = optimizer_config["param_grid"]

    combinations = list(product(*param_grid.values()))

    # Build long_dates
    long_date_ranges = optimizer_config.get("long_date_ranges", [])
    long_dates = pd.DatetimeIndex([])

    for start_str, end_str in long_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        long_dates = long_dates.union(pd.date_range(start=start, end=end, freq="30min"))

    short_date_ranges = optimizer_config.get("short_date_ranges", [])
    short_dates = pd.DatetimeIndex([])

    for start_str, end_str in short_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        short_dates = short_dates.union(pd.date_range(start=start, end=end, freq="30min"))

    csv_file = "data/es-30m-cleaned.csv"
    data = pd.read_csv(csv_file, parse_dates=[0], index_col=0)

    for i, combo in enumerate(combinations):
        ENTRY_OFFSET, TAKE_PROFIT_OFFSET, STOP_LOSS_OFFSET, TRAIL_TRIGGER, RE_ENTRY_DISTANCE, MAX_OPEN_TRADES, MAX_CONTRACTS_PER_TRADE = combo
        
        strategy = Strategy(
            name=f"Combo {i}",
            entry_offset=ENTRY_OFFSET,
            take_profit_offset=TAKE_PROFIT_OFFSET,
            stop_loss_offset=STOP_LOSS_OFFSET,
            trail_trigger=TRAIL_TRIGGER,
            re_entry_distance=RE_ENTRY_DISTANCE,
            max_open_trades=MAX_OPEN_TRADES,
            max_contracts_per_trade=MAX_CONTRACTS_PER_TRADE,
            long_dates=long_dates,
            short_dates=short_dates
        )

        strategy.load_static_levels(STATIC_LEVELS)
        
        backtester = StrategyBacktester()
        backtester.load_strategy(strategy)
        backtester.load_backtest_data(data)
        backtester.run_backtest()

        strategy.print_trade_stats()
        result = {
            'ENTRY_OFFSET': ENTRY_OFFSET,
            'TAKE_PROFIT_OFFSET': TAKE_PROFIT_OFFSET,
            'STOP_LOSS_OFFSET': STOP_LOSS_OFFSET,
            'TRAIL_TRIGGER': TRAIL_TRIGGER,
            'RE_ENTRY_DISTANCE': RE_ENTRY_DISTANCE,
            'MAX_OPEN_TRADES': MAX_OPEN_TRADES,
            'MAX_CONTRACTS_PER_TRADE': MAX_CONTRACTS_PER_TRADE,
            'TOTAL_PNL': strategy.total_pnl,
            'WIN_RATE': strategy.winrate,
            "AVERAGE_WINN": strategy.avgWinner,
            "AVERAGE_LOSS": strategy.avgLoser,
            "NUM_OF_TRADE": strategy.total_trade,
            "REWARD_TO_RISK": strategy.reward_to_risk,
        }

        results.append(result)

        # Write immediately to file
        df = pd.DataFrame([result])
        header = not os.path.exists(output_file)
        df.to_csv(output_file, mode='a', index=False, header=header)

    # Convert to DataFrame for analysis
    results_df = pd.DataFrame(results)
    print("Optimization result is available now!")
    # results_df.to_csv("optimizer_total_result.csv", index=False)