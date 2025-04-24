from datetime import date

import pandas as pd

from strategy import Strategy
from strategy_backtester import StrategyBacktester

# Create our example strategy.

LOTS_PER_TRADE = 3
# first set params
ENTRY_OFFSET = 8
STOP_LOSS_OFFSET = 100  # in ticks
TRAIL_TRIGGER = 2  # number of levels above entry trigger to set our stop
RE_ENTRY_DISTANCE = 2  # distance away from our original entry before we'll re-enter
MAX_OPEN_TRADES = LOTS_PER_TRADE * 1  # number of times you want to be able to trade LOTS PER TRADE before waiting to exit some positions
# All Static Levels from the PDF
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

STRATEGY_NAME = "Example Strategy One "

long_dates = pd.date_range(start=date(2000, 1, 1), end=date.today(), freq="30min")
short_dates = []

# create our strategy with our parameters
custom_strategy_one = Strategy(name=STRATEGY_NAME, entry_offset=ENTRY_OFFSET, stop_loss_offset=STOP_LOSS_OFFSET,
                               trail_trigger=TRAIL_TRIGGER, re_entry_distance=RE_ENTRY_DISTANCE, max_open_trades=MAX_OPEN_TRADES,
                               max_contracts_per_trade=LOTS_PER_TRADE, long_dates=long_dates, short_dates=short_dates)

# add our static levels
custom_strategy_one.load_static_levels(STATIC_LEVELS)

# Creating a second strategy
# ENTRY_OFFSET = 10
# STRATEGY_NAME = 'Example Strategy Two'
# STARTING_CASH_VALUE = float(input("Enter the starting cash value for strategy two: "))
# # leaving rest of params the same
# # same static levels for this one but you could update here
# custom_strategy_two = Strategy(name=STRATEGY_NAME, entry_offset=ENTRY_OFFSET, stop_loss_offset=STOP_LOSS_OFFSET,
#                                trail_trigger=TRAIL_TRIGGER, re_entry_distance=RE_ENTRY_DISTANCE,
#                                starting_cash_value=STARTING_CASH_VALUE, max_open_trades=MAX_OPEN_TRADES,
#                                max_contracts_per_trade=LOTS_PER_TRADE, long_dates=long_dates, short_dates=short_dates)

# custom_strategy_two.load_static_levels(STATIC_LEVELS.copy())  # made a copy

bt = StrategyBacktester()

# load our strategies into the backtester
bt.load_strategy(custom_strategy_one)
# bt.load_strategy(custom_strategy_two)

csv_file = "es-30m-cleaned.csv"
data = pd.read_csv(csv_file, parse_dates=[0], index_col=0)

bt.load_backtest_data(data)

bt.run_backtest()

bt.plot_backtest_results()
