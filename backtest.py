import json
from datetime import datetime, timedelta
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

from strategy.strategy import Strategy
from strategy.strategy_backtester import StrategyBacktester

# Load historical data
csv_file = "data/es-1m-cleaned.csv"
data = pd.read_csv(csv_file, parse_dates=[0], index_col=0)

# Initialize backtester
bt = StrategyBacktester()

# Load JSON config from .txt
with open("strategy/backtest_config.json", "r") as f:
    strategy_config = json.load(f)

    STATIC_LEVELS = strategy_config.get("static_levels", [])
    # Build long_dates
    long_date_ranges = strategy_config.get("long_date_ranges", [])
    long_dates = pd.DatetimeIndex([])

    for start_str, end_str in long_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        long_dates = long_dates.union(pd.date_range(start=start, end=end, freq="1min"))

    short_date_ranges = strategy_config.get("short_date_ranges", [])
    short_dates = pd.DatetimeIndex([])

    for start_str, end_str in short_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        short_dates = short_dates.union(pd.date_range(start=start, end=end, freq="1min"))

    # Optional: Define early close calendar for holidays
    # Example: {"2024-11-29": (12, 15), "2024-12-24": (12, 15)}
    early_close_calendar = strategy_config.get("early_close_calendar", {})

    strategy = Strategy(
        name=strategy_config["name"],
        trader=None,
        entry_offset=strategy_config["entry_offset"],
        take_profit_offset=strategy_config["take_profit_offset"],
        stop_loss_offset=strategy_config["stop_loss_offset"],
        trail_trigger=strategy_config["trail_trigger"],
        re_entry_distance=strategy_config["re_entry_distance"],
        max_open_trades=strategy_config["max_open_trades"],
        max_contracts_per_trade=strategy_config["max_contracts_per_trade"],
        long_dates=long_dates,
        short_dates=short_dates,
        symbol_size=50,
        is_trading_long=strategy_config.get("is_trading_long", True),
        use_trading_hours=strategy_config.get("use_trading_hours", True),
        early_close_calendar=early_close_calendar
    )

    strategy.load_static_levels(STATIC_LEVELS)
    bt.load_strategy(strategy)

    # Load data and run
    bt.load_backtest_data(data)

    bt.run_backtest()
    bt.strategies[0].print_trade_stats()

    # Export results to CSV
    s = bt.strategies[0]
    trades_df = pd.DataFrame(s.trade_history, columns=['timestamp', 'action', 'price', 'pnl'])
    trades_df['cumulative_pnl'] = trades_df['pnl'].cumsum()
    trades_df.to_csv('backtest_results.csv', index=False)
    print(f"\nResults saved to backtest_results.csv ({len(trades_df)} trades)")
