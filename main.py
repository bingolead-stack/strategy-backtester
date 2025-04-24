import json
from datetime import datetime, timedelta
import pandas as pd

from strategy import Strategy
from strategy_backtester import StrategyBacktester

# Load historical data
csv_file = "es-30m-cleaned.csv"
data = pd.read_csv(csv_file, parse_dates=[0], index_col=0)

# Initialize backtester
bt = StrategyBacktester()

STATIC_LEVELS = [
    31, 89.5, 148, 206.5, 265, 323.5, 382, 440.5, 499, 557.5, 616, 674.5, 733,
    791.5, 850, 908.5, 967, 1025.5, 1084, 1142.5, 1201, 1259.5, 1318, 1376.5,
    1435, 1493.5, 1552, 1610.5, 1669, 1727.5, 1786, 1844.5, 1903, 1961.5,
    2020, 2078.5, 2137, 2195.5, 2254, 2312.5, 2371, 2429.5, 2488, 2546.5,
    2605, 2663.5, 2722, 2780.5, 2839, 2897.5, 2956, 3014.5, 3073, 3131.5,
    3190, 3248.5, 3307, 3365.5, 3424, 3482.5, 3541, 3599.5, 3658, 3716.5,
    3775, 3833.5, 3892, 3950.5, 4009, 4067.5, 4126, 4184.5, 4243, 4301.5,
    4360, 4418.5, 4477, 4535.5, 4594, 4652.5, 4711, 4769.5, 4828, 4886.5,
    4945, 5003.5, 5062, 5120.5, 5179, 5237.5, 5296, 5354.5, 5413, 5471.5,
    5530, 5588.5, 5647, 5705.5, 5764, 5822.5, 5881, 5939.5, 5998, 6056.5,
    6115, 6173.5, 6232, 6290.5, 6349, 6407.5, 6466, 6524.5, 6583, 6641.5,
    6700, 6758.5, 6817, 6875.5, 6934, 6992.5, 7051, 7109.5, 7168, 7226.5,
    7285, 7343.5, 7402, 7460.5, 7519, 7577.5, 7636, 7694.5, 7753, 7811.5,
    7870, 7928.5, 7987
]
# Load JSON config from .txt
with open("strategy_config.json", "r") as f:
    strategy_config = json.load(f)
    long_dates = pd.date_range(
        start=pd.to_datetime(strategy_config["long_start"]),
        end=pd.to_datetime(strategy_config["long_end"]),
        freq="30min"
    ) if strategy_config["long_start"] and strategy_config["long_end"] else []

    short_dates = pd.date_range(
        start=pd.to_datetime(strategy_config["short_start"]),
        end=pd.to_datetime(strategy_config["short_end"]),
        freq="30min"
    ) if strategy_config["short_start"] and strategy_config["short_end"] else []
    
    excluded_ranges = strategy_config.get("excluded_date_ranges", [])
    excluded_dates = pd.DatetimeIndex([])

    for start_str, end_str in excluded_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        if start and end:
            excluded_dates = excluded_dates.union(pd.date_range(start=start, end=end, freq="30min"))

    long_dates_excluded = long_dates.difference(excluded_dates)

    strategy = Strategy(
        name=strategy_config["name"],
        entry_offset=strategy_config["entry_offset"],
        stop_loss_offset=strategy_config["stop_loss_offset"],
        trail_trigger=strategy_config["trail_trigger"],
        re_entry_distance=strategy_config["re_entry_distance"],
        max_open_trades=strategy_config["max_open_trades"],
        max_contracts_per_trade=strategy_config["max_contracts_per_trade"],
        long_dates=long_dates_excluded,
        short_dates=short_dates
    )

    strategy.load_static_levels(STATIC_LEVELS)
    bt.load_strategy(strategy)

    # Load data and run
    bt.load_backtest_data(data)

    bt.run_backtest()
    bt.plot_backtest_results()
