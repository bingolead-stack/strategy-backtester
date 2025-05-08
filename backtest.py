import json
from datetime import datetime, timedelta
import pandas as pd

from strategy.strategy import Strategy
from strategy.strategy_backtester import StrategyBacktester

# Load historical data
csv_file = "es-30m-cleaned.csv"
data = pd.read_csv(csv_file, parse_dates=[0], index_col=0)

# Initialize backtester
bt = StrategyBacktester()

# Load JSON config from .txt
with open("strategy_config.json", "r") as f:
    strategy_config = json.load(f)

    STATIC_LEVELS = strategy_config.get("static_levels", [])
    # Build long_dates
    long_date_ranges = strategy_config.get("long_date_ranges", [])
    long_dates = pd.DatetimeIndex([])

    for start_str, end_str in long_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        long_dates = long_dates.union(pd.date_range(start=start, end=end, freq="30min"))

    short_date_ranges = strategy_config.get("short_date_ranges", [])
    short_dates = pd.DatetimeIndex([])

    for start_str, end_str in short_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        short_dates = short_dates.union(pd.date_range(start=start, end=end, freq="30min"))

    strategy = Strategy(
        name=strategy_config["name"],
        entry_offset=strategy_config["entry_offset"],
        take_profit_offset=strategy_config["take_profit_offset"],
        stop_loss_offset=strategy_config["stop_loss_offset"],
        trail_trigger=strategy_config["trail_trigger"],
        re_entry_distance=strategy_config["re_entry_distance"],
        max_open_trades=strategy_config["max_open_trades"],
        max_contracts_per_trade=strategy_config["max_contracts_per_trade"],
        long_dates=long_dates,
        short_dates=short_dates
    )

    strategy.load_static_levels(STATIC_LEVELS)
    bt.load_strategy(strategy)

    # Load data and run
    bt.load_backtest_data(data)

    bt.run_backtest()
    bt.plot_backtest_results()
