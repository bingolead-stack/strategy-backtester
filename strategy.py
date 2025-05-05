from datetime import datetime
from typing import List

from matplotlib import pyplot as plt

class Strategy:

    def __init__(self, name: str, entry_offset, take_profit_offset, stop_loss_offset, trail_trigger, re_entry_distance,
                 max_open_trades, max_contracts_per_trade, long_dates, short_dates):
        """
        :param entry_offset: offset above signal to enter trade
        :param take_profit_offset: offset number of ticks above signal to close for profit
        :param stop_loss_offset: Offset, in ticks, that we stop ourselves out
        :param trail_trigger: Number of static levels before we trigger our trailing stop
        :param re_entry_distance: Distance beyond the retracement before we will re-enter our trade
        :param starting_cash_value: Initial cash available to this strategy
        :param max_open_trades: Maximum number of trades we can hold at any time

        """
        # Init strategy values
        self.is_trading = True
        self.name = name
        self.static_levels = None
        self.entry_offset = entry_offset / 4 # convert from ticks to price 
        self.take_profit_offset = take_profit_offset / 4 # convert from ticks to price
        self.stop_loss_offset = stop_loss_offset / 4  # convert from ticks to price
        self.trail_trigger = trail_trigger
        self.re_entry_distance = re_entry_distance
        self.max_open_trades = max_open_trades
        self.max_contracts_per_trade = max_contracts_per_trade

        # init stat data structs
        self.position = None
        self.entry_price = None
        self.stop_level = None
        self.trailing_stop = None
        self.trade_history = []
        self.traded_levels = {}
        self.current_cash_value = 0
        self.open_trade_count = 0
        self.open_trade_list = []

        # other misc stats
        self.total_pnl = 0
        self.cumulative_pnl = []
        self.winrate = 0
        self.avgWinner = 0
        self.avgLoser = 0
        self.total_trade = 0
        self.reward_to_risk = 0

        # current market state
        self.price = None
        self.last_price = None
        self.high_price = None
        self.index = None
        self.access_token = None

        # daterange stuff
        self.long_dates = long_dates
        self.short_dates = short_dates

    def load_static_levels(self, static_levels: List[int]):
        """

        :param static_levels: List of static levels
        :return: None, assigns our static levels for this strategy. Separate to init as we may want to have custom
        static level parsing
        """
        overwrite = False
        if self.static_levels is not None:
            overwrite = bool(input(
                "You already have static levels loaded. Do you want to overwrite? Type True to overwrite or False to ignore "))
        if not overwrite:
            self.static_levels = sorted(static_levels)

    def calculate_max_open_trades(self, price: float):
        """
        How our strategy sets risk
        :param price:
        :return:
        """
        # tick size is $12.50 per tick
        # margin is about 10% reounded up
        # margin_per_contract = 0.05 * 12.5 * 4 * price
        # max_open_trades = math.floor(self.current_cash_value / margin_per_contract)
        # return min(max_open_trades, self.max_open_trades)
        return self.max_open_trades - self.open_trade_count

    # TODO: make trading logic attach here instead of backtester
    def should_buy(self) -> bool:
        return True

    def should_sell(self) -> bool:
        return False

    def turn_off_trading(self):
        self.is_trading = False

    def run_buy_strategy(self):
        # need valid data

        max_open_trades = self.calculate_max_open_trades(self.price)
        # print(max_open_trades)
        if max_open_trades > 0:  # can trade
            for level in self.static_levels:
                entry_offset = self.entry_offset
                if self.price <= level < self.last_price:  # Retrace level
                    print(f"DEBUG: {self.name}: Price retraced to level {level} with price {self.price}.")

                    if level in self.traded_levels:  # If we've traded this level already
                        if abs(self.traded_levels[level] - self.price) >= self.re_entry_distance:
                            # Allow re-entry at this level
                            print(
                                f"DEBUG: {self.name}:  Current price {self.price} retraced to level {level}. We last traded at {self.traded_levels[level]}"
                                f" with additional offset of {self.re_entry_distance} we can now re-enter")

                            del self.traded_levels[level]  # Reset re-entry condition for this level

                        else:
                            print(
                                f"DEBUG: {self.name}: Level {level} already traded, re-entry condition not met.")
                            continue  # Skip this level, as re-entry condition is not met

                    # check if we can enter here (offset above entry level)
                    if self.price + entry_offset <= level:
                        for _ in range(self.max_contracts_per_trade):  # number of contracts to trade

                            entry_price = self.price
                            stop_level = self.price - self.stop_loss_offset
                            trailing_stop = None
                            self.position = 'long'
                            self.trade_history.append((self.index, 'BUY', entry_price, 0))  # pnl for buy trade is $0 since we haven't locked in any pnl yet

                            self.traded_levels[level] = self.price
                            
                            take_profit_level = entry_price + self.take_profit_offset
                            trade = [self.index, entry_price, stop_level, trailing_stop, level, take_profit_level]

                            # trade = [self.index, entry_price, stop_level, trailing_stop, level]  # store our open trades
                            self.open_trade_list.append(trade)
                            self.open_trade_count += 1
                            self.current_cash_value -= entry_price * 0.1 * 4 * 12.5

                            print(
                                f"{self.name}: [{self.index}] BUY ORDER SENT at {entry_price} (Retraced to static level {level})")
                            print(f"{self.name}: Stop-Loss Level: {stop_level}")
                            max_open_trades -= 1
        else:
            print(
                f"DEBUG: {self.name}: Open trade = {self.open_trade_count}, max open trades = {self.max_open_trades}. No room left to trade. Skipping")
        
    def run_sell_strategy(self):
        # need valid data

        max_open_trades = self.calculate_max_open_trades(self.price)
        if max_open_trades > 0:  # can trade
            for level in self.static_levels:
                entry_offset = self.entry_offset
                if self.price >= level > self.last_price:  # Retrace level upwards
                    print(f"DEBUG: {self.name}: Price retraced up to level {level}.")

                    if level in self.traded_levels:  # Already traded this level
                        if abs(self.traded_levels[level] - self.price) >= self.re_entry_distance:
                            print(
                                f"DEBUG: {self.name}: Current price {self.price} retraced up to level {level}. We last traded at {self.traded_levels[level]}"
                                f" with additional offset of {self.re_entry_distance} we can now re-enter")
                            del self.traded_levels[level]  # Allow re-entry
                        else:
                            print(
                                f"DEBUG: {self.name}: Level {level} already traded, re-entry condition not met.")
                            continue

                    if self.price - entry_offset >= level:
                        for _ in range(self.max_contracts_per_trade):  # number of contracts to trade

                            entry_price = self.price
                            stop_level = self.price + self.stop_loss_offset
                            trailing_stop = None
                            self.position = 'short'
                            self.trade_history.append((self.index, 'SELL', entry_price, 0))

                            self.traded_levels[level] = self.price

                            take_profit_level = entry_price - self.take_profit_offset
                            trade = [self.index, entry_price, stop_level, trailing_stop, level, take_profit_level]
                            self.open_trade_list.append(trade)
                            self.open_trade_count += 1
                            self.current_cash_value -= entry_price * 0.1 * 4 * 12.5

                            print(f"{self.name}: [{self.index}] SELL ORDER SENT at {entry_price} (Retraced up to static level {level})")
                            print(f"{self.name}: Stop-Loss Level: {stop_level}")
                            max_open_trades -= 1
        else:
            print(f"DEBUG: {self.name}: Open trade = {self.open_trade_count}, max open trades = {self.max_open_trades}. No room left to trade. Skipping")

    def check_trade_to_remove(self):
       if self.open_trade_count > 0:
            trades_to_remove = []
            for i in range(len(self.open_trade_list)):
                trade_time, entry_price, stop_level, trailing_stop, traded_level, take_profit_level  = self.open_trade_list[i]
                is_long_trade = entry_price < take_profit_level

                if is_long_trade:
                    if trailing_stop is None:
                        # Check if price has moved 2 levels above entry
                        index_of_level = self.static_levels.index(traded_level)  # find the level we triggered on
                        if len(self.static_levels) - 2 < index_of_level:  # we have no more levels to check so have to invalidate this trade #TODO: something smarter?
                            # del trade_history[-1]  # remove trade since we have no way to trigger a stop
                            raise ("ERROR ")  # hopefully this never happens but if it does, break until we fix this


                        trigger_price = self.static_levels[index_of_level + self.trail_trigger]  # find the price 2 levels up
                        if self.price >= trigger_price:
                            print(f"{self.name}: [{self.index}] Trailing stop activated for long position")
                            trailing_stop = trigger_price
                            self.open_trade_list[i][3] = trailing_stop  # update our trailing stop

                    if trailing_stop is not None:
                        # we take the closest price to the high of the day thats below it
                        highest_static_level = sorted([x for x in self.static_levels if x < self.high_price])[
                            -1]  # get highest value
                        trailing_stop = max(trailing_stop, highest_static_level)  # use high
                        self.open_trade_list[i][3] = trailing_stop  # update trailing stop

                    if self.price <= stop_level or (trailing_stop is not None and self.price <= trailing_stop) or (self.price >= take_profit_level):
                        # trade_history.append((index, 'SELL', price))

                        pnl = (self.price - entry_price) * 50  # mult be size
                        self.current_cash_value += pnl
                        # add tied up margin to the current cash
                        self.current_cash_value += entry_price * 0.1 * 4 * 12.5
                        self.total_pnl += pnl
                        self.trade_history.append((self.index, 'EXIT', self.price, pnl))
                        self.cumulative_pnl.append(self.total_pnl)

                        # clean up open trades
                        self.open_trade_count -= 1
                        trades_to_remove.append([trade_time, entry_price, stop_level, trailing_stop, traded_level, take_profit_level])

                        print(
                            f"[{self.index}] SELL ORDER EXECUTED at {self.price} (stop level hit {stop_level} or trailing stop hit at {trailing_stop})\n"
                            f"\t\t Profit/Loss: {pnl:.2f}")
                        print(f"    Entry Price: {entry_price}")
                        print(f"    Exit Price: {self.price}")
                        print(
                            f"    Trade Duration: {self.index - trade_time}")  # last two trades are our entry and exit

                else:
                    if trailing_stop is None:
                        index_of_level = self.static_levels.index(traded_level)
                        if index_of_level < self.trail_trigger:
                            raise ("ERROR")  # Not enough lower levels to use as trigger

                        trigger_price = self.static_levels[index_of_level - self.trail_trigger]
                        if self.price <= trigger_price:
                            print(f"{self.name}: [{self.index}] Trailing stop activated for short position")
                            trailing_stop = trigger_price
                            self.open_trade_list[i][3] = trailing_stop

                    if trailing_stop is not None:
                        # take the lowest static level above the low of the day
                        lowest_static_level = sorted([x for x in self.static_levels if x > self.low_price])[0]
                        trailing_stop = min(trailing_stop, lowest_static_level)
                        self.open_trade_list[i][3] = trailing_stop

                    if self.price >= stop_level or (trailing_stop is not None and self.price >= trailing_stop) or (self.price <= take_profit_level):
                        pnl = (entry_price - self.price) * 50
                        self.current_cash_value += pnl
                        self.current_cash_value += entry_price * 0.1 * 4 * 12.5
                        self.total_pnl += pnl
                        self.trade_history.append((self.index, 'EXIT', self.price, pnl))
                        self.cumulative_pnl.append(self.total_pnl)

                        self.open_trade_count -= 1
                        trades_to_remove.append([trade_time, entry_price, stop_level, trailing_stop, traded_level, take_profit_level])

                        print(
                            f"[{self.index}] COVER ORDER EXECUTED at {self.price} (stop level hit {stop_level} or trailing stop hit at {trailing_stop})\n"
                            f"\t\t Profit/Loss: {pnl:.2f}")
                        print(f"    Entry Price: {entry_price}")
                        print(f"    Exit Price: {self.price}")
                        print(f"    Trade Duration: {self.index - trade_time}")

            for trade in trades_to_remove:
                del self.open_trade_list[self.open_trade_list.index(trade)]  # remove the open trade


    def update(self, index: datetime, price: float, last_price: float, high_price: float, low_price: float):
        # check prices are valid
        if None in [price, last_price, high_price]:
            raise ValueError(f"Invalid data -> {price}, {last_price}, {high_price}")
        else:
            self.price = price
            self.last_price = last_price
            self.high_price = high_price
            self.low_price = low_price
            self.index = index

            if index in self.long_dates:
                self.run_buy_strategy()
            elif index in self.short_dates:
                self.run_sell_strategy()

            self.check_trade_to_remove()

    def print_trade_stats(self):
        # Print Trade Summary
        # for trade in trade_history:
        #     print(f"{trade[0]}: {trade[1]} at {trade[2]}, PnL: {trade[3] if len(trade) > 2 else 'N/A'}")
        print(f"Total Pnl for {self.name}: ${self.total_pnl}")

        # Trade Statistics
        wins = [trade[3] for trade in self.trade_history if trade[1] == 'EXIT' and trade[3] > 0]
        losses = [trade[3] for trade in self.trade_history if trade[1] == 'EXIT' and trade[3] <= 0]
        win_percentage = len(wins) / max(1, (len(wins) + len(losses))) * 100
        lose_percentage = len(losses) / max(1, (len(wins) + len(losses))) * 100
        biggest_winner = max(wins, default=0)
        biggest_loser = min(losses, default=0)
        average_winner = sum(wins) / max(1, len(wins))
        average_loser = sum(losses) / max(1, len(losses))
        self.avgWinner = average_winner
        self.avgLoser = average_loser
        self.winrate = win_percentage
        self.total_trade = len(wins) + len(losses)
        self.reward_to_risk = average_winner / max(1, abs(average_loser))

        print(f"\n{self.name} | Trade Statistics:")
        print(f"Win %: {win_percentage:.2f}%, Lose %: {lose_percentage:.2f}%")
        print(f"Biggest Winner: {biggest_winner:.2f}")
        print(f"Biggest Loser: {biggest_loser:.2f}")
        print(f"Average Winner: {average_winner:.2f}")
        print(f"Average Loser: {average_loser:.2f}")
        print(f"Total PnL: {self.total_pnl:.2f}")
        print(f"Total Trade made: {self.total_trade}")

    def plot_trades(self, instrument_data):

        # Plot Price and Trade Entries
        plt.figure(figsize=(10, 5))
        plt.plot(instrument_data.index, instrument_data['close'], label='Price')
        for trade in self.trade_history:
            if trade[1] == "EXIT":
                continue
            color = 'g' if trade[1] == 'BUY' else 'r'
            plt.scatter(trade[0], trade[2], color=color)

        # Add horizontal lines for static levels
        for level in self.static_levels:
            plt.axhline(y=level, color='gray', linestyle='--', linewidth=0.5)
                
        plt.legend()
        plt.title(f"Price and Trade Entries for {self.name}")
        plt.show()

        # Plot Cumulative PnL
        plt.figure(figsize=(10, 5))
        plt.plot([x[0] for x in self.trade_history if x[1] == 'EXIT'], self.cumulative_pnl,
                 label='Cumulative PnL', color='b')
        plt.legend()
        plt.title(f"Cumulative PnL for {self.name}")
        plt.show()

# put in date ranges to trade/not trade
