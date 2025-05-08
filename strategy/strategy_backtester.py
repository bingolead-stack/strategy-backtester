from typing import List, Optional

import pandas as pd

import matplotlib.pyplot as plt

from strategy.strategy import Strategy


class StrategyBacktester:

    def __init__(self):
        """

        """
        self.strategies: List[Strategy] = []
        self.data: Optional[pd.DataFrame] = None

    def load_strategies(self, strategies: List[Strategy]) -> None:
        """

        :param strategies: an array of strategy objects
        :return:
        """
        self.strategies = strategies

    def load_strategy(self, strategy: Strategy) -> None:
        """

        :param strategy: A single strategy
        :return:
        """
        self.strategies.append(strategy)

    def load_backtest_data(self, df: pd.DataFrame) -> None:
        """

        :param df: our backtest data
        :return:
        """
        self.data = df

    def run_backtest(self) -> None:

        """
        Runs a backtest and outputs the stats
        :return:
        """
        last_price = None
        # Backtest Strategy
        for index, row in self.data.iterrows():
            price = row['close']  # update current price
            high_price = row['high']
            low_price = row['low']
            

            if last_price is None:  # cant trade without a valid last price
                last_price = price
                continue
            for strategy in self.strategies:
                # pass the relevant price information
                
                strategy.update(index, price, last_price, high_price, low_price)

            # update
            last_price = price  # update previous price

        

    def plot_backtest_results(self):
        for strategy in self.strategies:
            strategy.print_trade_stats()
            strategy.plot_trades(self.data)
