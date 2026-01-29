from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set
from matplotlib import pyplot as plt
import logging

from lib.tradovate_api import TradovateTrader
from lib.state_persistence import StatePersistence
from lib.cme_trading_hours import CMETradingHours

# Get strategy logger - only logger used
strategy_logger = logging.getLogger('strategy')

class Strategy:

    def __init__(self, name: str, trader:TradovateTrader, entry_offset, take_profit_offset, stop_loss_offset, trail_trigger, re_entry_distance,
                 max_open_trades, max_contracts_per_trade, long_dates = None, short_dates = None, symbol_size=50, is_trading_long = True,
                 persistence: Optional[StatePersistence] = None, auto_save: bool = True,
                 use_trading_hours: bool = True, early_close_calendar: Optional[Dict[str, tuple]] = None):
        """
        :param entry_offset: offset above signal to enter trade
        :param take_profit_offset: offset number of ticks above signal to close for profit
        :param stop_loss_offset: Offset, in ticks, that we stop ourselves out
        :param trail_trigger: Number of static levels before we trigger our trailing stop
        :param re_entry_distance: Distance beyond the retracement before we will re-enter our trade
        :param starting_cash_value: Initial cash available to this strategy
        :param max_open_trades: Maximum number of trades we can hold at any time
        :param persistence: StatePersistence instance for saving/loading state
        :param auto_save: Whether to automatically save state after each update
        :param use_trading_hours: Whether to enforce CME trading hours (flatten before close, no new trades during close)
        :param early_close_calendar: Dict mapping date strings (YYYY-MM-DD) to early close times as (hour, minute) tuples

        """
        # Init strategy values
        self.is_trading = True
        self.name = name
        self.trader = trader
        self.static_levels = None
        self.entry_offset = entry_offset / 4 # convert from ticks to price 
        self.take_profit_offset = take_profit_offset / 4 # convert from ticks to price
        self.stop_loss_offset = stop_loss_offset / 4  # convert from ticks to price
        self.trail_trigger = trail_trigger
        self.re_entry_distance = re_entry_distance
        self.max_open_trades = max_open_trades
        self.max_contracts_per_trade = max_contracts_per_trade
        self.symbol_size = symbol_size

        # init stat data structs
        self.position = None
        self.entry_price = None
        self.stop_level = None
        self.trailing_stop = None
        self.trade_history = []
        self.current_cash_value = 0
        self.open_trade_count = 0
        self.open_trade_list = []
        self.retrace_levels = {}

        # other misc stats
        self.total_pnl = 0
        self.cumulative_pnl = []
        self.winrate = 0
        self.avgWinner = 0
        self.avgLoser = 0
        self.total_trade = 0
        self.reward_to_risk = 0
        self.max_losing_streak = 0

        # current market state
        self.price = None
        self.last_price = None
        self.high_price = None
        self.low_price = None
        self.index = None

        # daterange stuff
        self.long_dates = long_dates
        self.short_dates = short_dates
        self.is_trading_long = is_trading_long
        
        # persistence
        self.persistence = persistence
        self.auto_save = auto_save

        # CME trading hours
        self.use_trading_hours = use_trading_hours
        self.trading_hours = CMETradingHours(early_close_calendar) if use_trading_hours else None
        self._positions_flattened_today = False
        self._last_flatten_date = None

        # Entry rate limiting - prevent duplicate entries
        self._entries_this_bar: Set[int] = set()  # Track level indices entered this bar
        self._last_bar_index: Optional[datetime] = None  # Track current bar timestamp
        self._last_entry_time: Optional[datetime] = None  # Track last entry time
        self.MIN_ENTRY_INTERVAL_MINUTES = 5  # Minimum minutes between entries

    def load_static_levels(self, static_levels: List[int]):
        self.static_levels = sorted(static_levels)
        # Store direction of level cross: 'up', 'down', or None
        self.retrace_levels = {i: None for i in range(len(static_levels))}
    
    def get_state(self) -> dict:
        """
        Get current strategy state as a dictionary for persistence.
        
        Returns:
            Dictionary containing all strategy state
        """
        return {
            'current_cash_value': self.current_cash_value,
            'open_trade_count': self.open_trade_count,
            'total_pnl': self.total_pnl,
            'price': self.price,
            'last_price': self.last_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'index': str(self.index) if self.index else None,
            'winrate': self.winrate,
            'avg_winner': self.avgWinner,
            'avg_loser': self.avgLoser,
            'total_trade': self.total_trade,
            'reward_to_risk': self.reward_to_risk,
            'max_losing_streak': self.max_losing_streak,
            'trade_history': self.trade_history,
            'open_trade_list': self.open_trade_list,
            'retrace_levels': self.retrace_levels,
            'cumulative_pnl': self.cumulative_pnl,
            'static_levels': self.static_levels,
            'last_entry_time': str(self._last_entry_time) if self._last_entry_time else None,
            'entries_this_bar': list(self._entries_this_bar),
            'last_bar_index': str(self._last_bar_index) if self._last_bar_index else None
        }
    
    def _parse_datetime(self, value):
        """
        Helper function to parse datetime from string or return datetime object.
        
        Args:
            value: String or datetime object
            
        Returns:
            datetime object or None
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                # Try alternative formats if fromisoformat fails
                try:
                    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    try:
                        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return None
        return None
    
    def _calculate_duration(self, start_time, end_time):
        """
        Helper function to safely calculate duration between two times.
        
        Args:
            start_time: datetime object or string
            end_time: datetime object or string
            
        Returns:
            timedelta object or string representation if calculation fails
        """
        start = self._parse_datetime(start_time)
        end = self._parse_datetime(end_time)
        
        if start is None or end is None:
            return "N/A"
        
        try:
            return end - start
        except TypeError:
            return "N/A"
    
    def set_state(self, state: dict):
        """
        Restore strategy state from a dictionary.
        
        Args:
            state: Dictionary containing strategy state
        """
        self.current_cash_value = state.get('current_cash_value', 0)
        self.open_trade_count = state.get('open_trade_count', 0)
        self.total_pnl = state.get('total_pnl', 0)
        self.price = state.get('price')
        self.last_price = state.get('last_price')
        self.high_price = state.get('high_price')
        self.low_price = state.get('low_price')
        
        # Handle index - it might be stored as string in DB
        index_val = state.get('index')
        if index_val:
            self.index = self._parse_datetime(index_val)
        else:
            self.index = None
        
        self.winrate = state.get('winrate', 0)
        self.avgWinner = state.get('avg_winner', 0)
        self.avgLoser = state.get('avg_loser', 0)
        self.total_trade = state.get('total_trade', 0)
        self.reward_to_risk = state.get('reward_to_risk', 0)
        self.max_losing_streak = state.get('max_losing_streak', 0)
        
        # Convert trade_history datetime strings back to datetime objects
        trade_history = state.get('trade_history', [])
        self.trade_history = []
        for trade in trade_history:
            if len(trade) >= 4:
                trade_time = self._parse_datetime(trade[0])
                self.trade_history.append((trade_time, trade[1], trade[2], trade[3]))
            else:
                self.trade_history.append(trade)
        
        # Convert open_trade_list datetime strings back to datetime objects
        open_trade_list = state.get('open_trade_list', [])
        self.open_trade_list = []
        for trade in open_trade_list:
            if len(trade) >= 6:
                trade_time = self._parse_datetime(trade[0])
                self.open_trade_list.append([trade_time, trade[1], trade[2], trade[3], trade[4], trade[5]])
            else:
                self.open_trade_list.append(trade)
        
        # Convert retrace_levels - keys might be strings from DB, need to be integers
        retrace_levels_raw = state.get('retrace_levels', {})
        self.retrace_levels = {}
        for key, value in retrace_levels_raw.items():
            # Convert string keys back to integers
            int_key = int(key) if isinstance(key, str) else key
            self.retrace_levels[int_key] = value
        
        self.cumulative_pnl = state.get('cumulative_pnl', [])
        
        # Static levels should already be loaded via load_static_levels()
        # but can restore from state if needed
        if state.get('static_levels') and not self.static_levels:
            self.static_levels = state['static_levels']

        # Restore entry rate limiting state
        last_entry_time = state.get('last_entry_time')
        self._last_entry_time = self._parse_datetime(last_entry_time) if last_entry_time else None

        entries_this_bar = state.get('entries_this_bar', [])
        self._entries_this_bar = set(entries_this_bar)

        last_bar_index = state.get('last_bar_index')
        self._last_bar_index = self._parse_datetime(last_bar_index) if last_bar_index else None
    
    def save_state(self):
        """Save current strategy state to database if persistence is enabled."""
        if self.persistence and self.auto_save:
            try:
                state = self.get_state()
                self.persistence.save_strategy_state(self.name, state)
            except Exception as e:
                strategy_logger.error(f"Failed to save state for {self.name}: {e}", exc_info=True)
    
    def load_state(self) -> bool:
        """
        Load strategy state from database if available.
        
        Returns:
            True if state was loaded, False otherwise
        """
        if self.persistence:
            try:
                state = self.persistence.load_strategy_state(self.name)
                if state:
                    strategy_logger.info(f"📂 Loading state from DB for {self.name}:")
                    strategy_logger.info(f"   DB shows: Open trades={state.get('open_trade_count')}, Open list size={len(state.get('open_trade_list', []))}, PnL=${state.get('total_pnl', 0):.2f}")
                    
                    self.set_state(state)
                    
                    active_retraces = [(k, v) for k, v in self.retrace_levels.items() if v is not None]
                    strategy_logger.info(f"✓ State loaded for {self.name}:")
                    strategy_logger.info(f"   After restore: Open trades={self.open_trade_count}, Open list size={len(self.open_trade_list)}, Active retraces={len(active_retraces)}")
                    return True
                else:
                    strategy_logger.info(f"Starting fresh - No saved state for {self.name}")
            except Exception as e:
                strategy_logger.error(f"Failed to load state for {self.name}: {e}", exc_info=True)
        return False

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

        # Reset per-bar entry tracking when bar changes
        if self.index != self._last_bar_index:
            self._entries_this_bar = set()
            self._last_bar_index = self.index

        max_open_trades = self.calculate_max_open_trades(self.price)
        level_crossed = False

        # ALWAYS track level crosses regardless of whether we can trade
        for level in self.static_levels:
            level_idx = self.static_levels.index(level)
            
            # Track direction of level cross
            if self.price <= level < self.high_price:  # Price crossed DOWN through level
                level_crossed = True
                strategy_logger.info(f"{self.name}: Price crossed DOWN through level {level} (level_idx={level_idx})")
                strategy_logger.info(f"  Current price: {self.price}, High: {self.high_price}, Level: {level}")
                self.retrace_levels[level_idx] = 'down'
            elif self.price >= level > self.low_price:  # Price crossed UP through level
                level_crossed = True
                strategy_logger.info(f"{self.name}: Price crossed UP through level {level} (level_idx={level_idx})")
                strategy_logger.info(f"  Current price: {self.price}, Low: {self.low_price}, Level: {level}")
                self.retrace_levels[level_idx] = 'up'
        
        # Only check entry conditions if we have room to trade
        if max_open_trades > 0:  # can trade
            for level in self.static_levels:
                entry_offset = self.entry_offset
                level_idx = self.static_levels.index(level)

                # For long strategy, enter when price crosses up after a down retrace
                re_entry_idx = level_idx + self.re_entry_distance
                
                # Check entry conditions
                condition1 = self.price <= level + entry_offset < self.last_price
                condition2 = re_entry_idx in self.retrace_levels
                condition3 = self.retrace_levels.get(re_entry_idx) == 'down' if condition2 else False
                
                # Log detailed decision process when price crosses this level or nearby
                if abs(self.price - level) < 50:  # Near this level
                    if condition1 or level_crossed:  # Price action happening
                        strategy_logger.info(f"{self.name}: Evaluating LONG entry at level {level}")
                        strategy_logger.info(f"  Step 1 - Price crossed down through entry zone?")
                        strategy_logger.info(f"    Price: {self.price}, Entry threshold: {level + entry_offset}, Last price: {self.last_price}")
                        strategy_logger.info(f"    Result: {'YES' if condition1 else 'NO'}")
                        
                        if condition1:
                            strategy_logger.info(f"  Step 2 - Does re-entry level {re_entry_idx} exist?")
                            strategy_logger.info(f"    Result: {'YES' if condition2 else 'NO'}")
                            
                            if condition2:
                                strategy_logger.info(f"  Step 3 - Is re-entry level {re_entry_idx} marked as 'down' retrace?")
                                strategy_logger.info(f"    Current value: '{self.retrace_levels.get(re_entry_idx)}'")
                                strategy_logger.info(f"    Result: {'YES - ENTRY CONDITIONS MET!' if condition3 else 'NO - Need down retrace'}")
                            else:
                                strategy_logger.info(f"  Decision: Cannot enter - Re-entry index {re_entry_idx} not in retrace_levels")
                        else:
                            strategy_logger.info(f"  Decision: Cannot enter - Price hasn't crossed down through entry zone")
                
                if condition1 and condition2 and condition3:
                    # Check if this level was already entered this bar
                    if level_idx in self._entries_this_bar:
                        strategy_logger.info(f"{self.name}: Skipping entry at level {level} - already entered this bar")
                        continue

                    # Check minimum time between entries
                    if self._last_entry_time is not None:
                        time_since_last = self.index - self._last_entry_time
                        if time_since_last < timedelta(minutes=self.MIN_ENTRY_INTERVAL_MINUTES):
                            strategy_logger.info(f"{self.name}: Skipping entry at level {level} - only {time_since_last} since last entry (min: {self.MIN_ENTRY_INTERVAL_MINUTES} min)")
                            continue

                    strategy_logger.info(f"{self.name}: *** ENTRY TRIGGERED *** at level {level} (level_idx={level_idx}, re_entry_idx={re_entry_idx})")
                    strategy_logger.info(f"  - Price: {self.price}, Last: {self.last_price}, Entry threshold: {level + entry_offset}")
                    strategy_logger.info(f"  - Retrace level {re_entry_idx} direction: {self.retrace_levels[re_entry_idx]}")
                    self.retrace_levels[re_entry_idx] = None  # Clear the retrace flag
                    # Now the entry condition met. We can enter trade here.
                    for _ in range(self.max_contracts_per_trade):  # number of contracts to trade
                        entry_price = self.price
                        stop_level = entry_price - self.stop_loss_offset
                        trailing_stop = None
                        take_profit_level = entry_price + self.take_profit_offset
                        trade = [self.index, entry_price, stop_level, trailing_stop, level, take_profit_level]

                        strategy_logger.info(f"{self.name}: [{self.index}] BUY ORDER SENT at {entry_price} (Retraced to static level {level})")
                        strategy_logger.info(f"{self.name}: Stop-Loss Level: {stop_level}")

                        order_success = False
                        if self.trader is not None:
                            order_success = self.trader.enter_position(quantity=1, is_long=True)
                        else:
                            # If no trader, assume success for backtesting
                            order_success = True

                        if order_success:
                            self.position = 'long'
                            self.trade_history.append((self.index, 'BUY', entry_price, 0))  # pnl for buy trade is $0 since we haven't locked in any pnl yet
                            self.open_trade_list.append(trade)
                            self.open_trade_count += 1
                            self.current_cash_value -= entry_price * 0.1 * 4 * 12.5
                            max_open_trades -= 1
                            # Track this entry
                            self._entries_this_bar.add(level_idx)
                            self._last_entry_time = self.index
                            strategy_logger.info(f"{self.name}: ✓ Order executed successfully. Open trades: {self.open_trade_count} (list size: {len(self.open_trade_list)})")
                        else:
                            strategy_logger.warning(f"{self.name}: ✗ Order FAILED. Trade not added to list.")

        else:
            if self.open_trade_count >= self.max_open_trades:
                strategy_logger.info(f"{self.name}: No room to trade (Open: {self.open_trade_count}/{self.max_open_trades})")
        
    def run_sell_strategy(self):
        # need valid data

        # Reset per-bar entry tracking when bar changes
        if self.index != self._last_bar_index:
            self._entries_this_bar = set()
            self._last_bar_index = self.index

        max_open_trades = self.calculate_max_open_trades(self.price)
        level_crossed = False

        # ALWAYS track level crosses regardless of whether we can trade
        for level in self.static_levels:
            level_idx = self.static_levels.index(level)
            
            # Track direction of level cross
            if self.price >= level > self.low_price:  # Price crossed UP through level
                level_crossed = True
                strategy_logger.info(f"{self.name}: Price crossed UP through level {level} (level_idx={level_idx})")
                strategy_logger.info(f"  Current price: {self.price}, Low: {self.low_price}, Level: {level}")
                self.retrace_levels[level_idx] = 'up'
            elif self.price <= level < self.high_price:  # Price crossed DOWN through level
                level_crossed = True
                strategy_logger.info(f"{self.name}: Price crossed DOWN through level {level} (level_idx={level_idx})")
                strategy_logger.info(f"  Current price: {self.price}, High: {self.high_price}, Level: {level}")
                self.retrace_levels[level_idx] = 'down'
        
        # Only check entry conditions if we have room to trade
        if max_open_trades > 0:  # can trade
            for level in self.static_levels:
                entry_offset = self.entry_offset
                level_idx = self.static_levels.index(level)
                
                # For short strategy, enter when price crosses down after an up retrace
                re_entry_idx = level_idx - self.re_entry_distance
                
                # Check entry conditions
                condition1 = self.price > level - entry_offset >= self.last_price
                condition2 = re_entry_idx in self.retrace_levels
                condition3 = self.retrace_levels.get(re_entry_idx) == 'up' if condition2 else False
                
                # Log detailed decision process when price crosses this level or nearby
                if abs(self.price - level) < 50:  # Near this level
                    if condition1 or level_crossed:  # Price action happening
                        strategy_logger.info(f"{self.name}: Evaluating SHORT entry at level {level}")
                        strategy_logger.info(f"  Step 1 - Price crossed up through entry zone?")
                        strategy_logger.info(f"    Price: {self.price}, Entry threshold: {level - entry_offset}, Last price: {self.last_price}")
                        strategy_logger.info(f"    Result: {'YES' if condition1 else 'NO'}")
                        
                        if condition1:
                            strategy_logger.info(f"  Step 2 - Does re-entry level {re_entry_idx} exist?")
                            strategy_logger.info(f"    Result: {'YES' if condition2 else 'NO'}")
                            
                            if condition2:
                                strategy_logger.info(f"  Step 3 - Is re-entry level {re_entry_idx} marked as 'up' retrace?")
                                strategy_logger.info(f"    Current value: '{self.retrace_levels.get(re_entry_idx)}'")
                                strategy_logger.info(f"    Result: {'YES - ENTRY CONDITIONS MET!' if condition3 else 'NO - Need up retrace'}")
                            else:
                                strategy_logger.info(f"  Decision: Cannot enter - Re-entry index {re_entry_idx} not in retrace_levels")
                        else:
                            strategy_logger.info(f"  Decision: Cannot enter - Price hasn't crossed up through entry zone")
                
                if condition1 and condition2 and condition3:
                    # Check if this level was already entered this bar
                    if level_idx in self._entries_this_bar:
                        strategy_logger.info(f"{self.name}: Skipping entry at level {level} - already entered this bar")
                        continue

                    # Check minimum time between entries
                    if self._last_entry_time is not None:
                        time_since_last = self.index - self._last_entry_time
                        if time_since_last < timedelta(minutes=self.MIN_ENTRY_INTERVAL_MINUTES):
                            strategy_logger.info(f"{self.name}: Skipping entry at level {level} - only {time_since_last} since last entry (min: {self.MIN_ENTRY_INTERVAL_MINUTES} min)")
                            continue

                    strategy_logger.info(f"{self.name}: *** ENTRY TRIGGERED *** at level {level} (level_idx={level_idx}, re_entry_idx={re_entry_idx})")
                    strategy_logger.info(f"  - Price: {self.price}, Last: {self.last_price}, Entry threshold: {level - entry_offset}")
                    strategy_logger.info(f"  - Retrace level {re_entry_idx} direction: {self.retrace_levels[re_entry_idx]}")
                    self.retrace_levels[re_entry_idx] = None  # Clear the retrace flag

                    # We can enter trade here.
                    for _ in range(self.max_contracts_per_trade):  # number of contracts to trade
                        entry_price = self.price
                        stop_level = self.price + self.stop_loss_offset
                        trailing_stop = None
                        take_profit_level = entry_price - self.take_profit_offset
                        trade = [self.index, entry_price, stop_level, trailing_stop, level, take_profit_level]

                        strategy_logger.info(f"{self.name}: [{self.index}] SELL ORDER SENT at {entry_price} (Retraced up to static level {level})")
                        strategy_logger.info(f"{self.name}: Stop-Loss Level: {stop_level}")

                        order_success = False
                        if self.trader is not None:
                            order_success = self.trader.enter_position(quantity=1, is_long=False)
                        else:
                            # If no trader, assume success for backtesting
                            order_success = True

                        if order_success:
                            self.position = 'short'
                            self.trade_history.append((self.index, 'SELL', entry_price, 0))
                            self.open_trade_list.append(trade)
                            self.open_trade_count += 1
                            self.current_cash_value -= entry_price * 0.1 * 4 * 12.5
                            max_open_trades -= 1
                            # Track this entry
                            self._entries_this_bar.add(level_idx)
                            self._last_entry_time = self.index
                            strategy_logger.info(f"{self.name}: ✓ Order executed successfully. Open trades: {self.open_trade_count} (list size: {len(self.open_trade_list)})")
                        else:
                            strategy_logger.warning(f"{self.name}: ✗ Order FAILED. Trade not added to list.")

        else:
            if self.open_trade_count >= self.max_open_trades:
                strategy_logger.info(f"{self.name}: No room to trade (Open: {self.open_trade_count}/{self.max_open_trades})")

    def flatten_all_positions(self, reason: str = "Market close"):
        """
        Flatten (close) all open positions.

        Args:
            reason: Reason for flattening (for logging)
        """
        if self.open_trade_count == 0:
            return

        strategy_logger.info(f"{self.name}: FLATTENING ALL POSITIONS - {reason}")
        strategy_logger.info(f"{self.name}: Closing {self.open_trade_count} open trades")

        total_flatten_pnl = 0

        for trade in self.open_trade_list[:]:  # Use slice copy to iterate safely
            trade_time, entry_price, stop_level, trailing_stop, traded_level, take_profit_level = trade
            is_long_trade = entry_price < take_profit_level

            if is_long_trade:
                pnl = (self.price - entry_price) * self.symbol_size
            else:
                pnl = (entry_price - self.price) * self.symbol_size

            self.current_cash_value += pnl
            self.current_cash_value += entry_price * 0.1 * 4 * 12.5  # Return margin
            self.total_pnl += pnl
            total_flatten_pnl += pnl

            self.trade_history.append((self.index, 'FLATTEN', self.price, pnl))
            self.cumulative_pnl.append(self.total_pnl)

            # Exit via trader if connected
            if self.trader is not None:
                if is_long_trade:
                    self.trader.enter_position(quantity=1, is_long=False)
                else:
                    self.trader.enter_position(quantity=1, is_long=True)

            strategy_logger.info(f"{self.name}: {'LONG' if is_long_trade else 'SHORT'} FLATTEN at {self.price} | "
                               f"PnL: ${pnl:.2f} | Entry: {entry_price} | Duration: {self._calculate_duration(trade_time, self.index)}")

        # Clear all open trades
        self.open_trade_list = []
        self.open_trade_count = 0
        self.position = None

        strategy_logger.info(f"{self.name}: All positions flattened. Total flatten PnL: ${total_flatten_pnl:.2f}")

    def check_trade_to_remove(self):
       if self.open_trade_count > 0:
            trades_to_remove = []
            for i in range(len(self.open_trade_list)):
                trade_time, entry_price, stop_level, trailing_stop, traded_level, take_profit_level  = self.open_trade_list[i]
                
                # Ensure trade_time is a datetime object (convert from string if needed)
                if not isinstance(trade_time, datetime):
                    trade_time = self._parse_datetime(trade_time)
                    if trade_time is None:
                        # Skip this trade if we can't parse the datetime
                        strategy_logger.warning(f"Could not parse trade_time for trade {i}, skipping")
                        continue
                    # Update the list with the parsed datetime
                    self.open_trade_list[i][0] = trade_time
                
                is_long_trade = entry_price < take_profit_level

                if is_long_trade:
                    if trailing_stop is None:
                        # Check if price has moved 2 levels above entry
                        index_of_level = self.static_levels.index(traded_level)  # find the level we triggered on
                        if len(self.static_levels) - 2 < index_of_level:  # we have no more levels to check so have to invalidate this trade #TODO: something smarter?
                            # del trade_history[-1]  # remove trade since we have no way to trigger a stop
                            raise ("ERROR ")  # hopefully this never happens but if it does, break until we fix this


                        trigger_price = self.static_levels[index_of_level + self.trail_trigger]  # find the price 2 levels up
                        if self.price > trigger_price:
                            strategy_logger.info(f"{self.name}: Trailing stop activated for LONG at {trigger_price}")
                            trailing_stop = trigger_price
                            self.open_trade_list[i][3] = trailing_stop  # update our trailing stop

                    if trailing_stop is not None:
                        trailing_stop = max(trailing_stop, self.price - self.stop_loss_offset)  # use high
                        self.open_trade_list[i][3] = trailing_stop  # update trailing stop

                    if self.price <= stop_level or (trailing_stop is not None and self.price <= trailing_stop) or (self.price >= take_profit_level):
                        # trade_history.append((index, 'SELL', price))

                        pnl = (self.price - entry_price) * self.symbol_size  # mult be size
                        self.current_cash_value += pnl
                        # add tied up margin to the current cash
                        self.current_cash_value += entry_price * 0.1 * 4 * 12.5
                        self.total_pnl += pnl
                        self.trade_history.append((self.index, 'EXIT', self.price, pnl))
                        self.cumulative_pnl.append(self.total_pnl)

                        # clean up open trades
                        self.open_trade_count -= 1
                        trades_to_remove.append([trade_time, entry_price, stop_level, trailing_stop, traded_level, take_profit_level])
                        if self.trader is not None:
                            netPosition = self.trader.get_net_position()
                            if netPosition > 0:
                                self.trader.enter_position(quantity=1, is_long=False)

                        reason = "Trailing stop" if trailing_stop and self.price <= trailing_stop else ("Stop loss" if self.price <= stop_level else "Take profit")
                        strategy_logger.info(f"{self.name}: LONG EXIT - {reason} at {self.price} | PnL: ${pnl:.2f} | Entry: {entry_price} | Duration: {self._calculate_duration(trade_time, self.index)}")
                        strategy_logger.info(f"{self.name}: Open trade count decreased to {self.open_trade_count}")

                else:
                    if trailing_stop is None:
                        index_of_level = self.static_levels.index(traded_level)
                        if index_of_level < self.trail_trigger:
                            raise ("ERROR")  # Not enough lower levels to use as trigger

                        trigger_price = self.static_levels[index_of_level - self.trail_trigger]
                        if self.price <= trigger_price:
                            strategy_logger.info(f"{self.name}: Trailing stop activated for SHORT at {trigger_price}")
                            trailing_stop = trigger_price
                            self.open_trade_list[i][3] = trailing_stop

                    if trailing_stop is not None:
                        # take the lowest static level above the low of the day
                        # lowest_static_level = sorted([x for x in self.static_levels if x > self.low_price])[0]
                        trailing_stop = min(trailing_stop, self.price + self.stop_loss_offset)
                        self.open_trade_list[i][3] = trailing_stop

                    if self.price >= stop_level or (trailing_stop is not None and self.price >= trailing_stop) or (self.price <= take_profit_level):
                        pnl = (entry_price - self.price) * self.symbol_size
                        self.current_cash_value += pnl
                        self.current_cash_value += entry_price * 0.1 * 4 * 12.5
                        self.total_pnl += pnl
                        self.trade_history.append((self.index, 'EXIT', self.price, pnl))
                        self.cumulative_pnl.append(self.total_pnl)

                        self.open_trade_count -= 1
                        trades_to_remove.append([trade_time, entry_price, stop_level, trailing_stop, traded_level, take_profit_level])
                        
                        if self.trader is not None:
                            netPosition = self.trader.get_net_position()
                            if netPosition < 0:
                                self.trader.enter_position(quantity=1, is_long=True)
                        
                        reason = "Trailing stop" if trailing_stop and self.price >= trailing_stop else ("Stop loss" if self.price >= stop_level else "Take profit")
                        strategy_logger.info(f"{self.name}: SHORT EXIT - {reason} at {self.price} | PnL: ${pnl:.2f} | Entry: {entry_price} | Duration: {self._calculate_duration(trade_time, self.index)}")
                        strategy_logger.info(f"{self.name}: Open trade count decreased to {self.open_trade_count}")

            for trade in trades_to_remove:
                del self.open_trade_list[self.open_trade_list.index(trade)]  # remove the open trade
            
            # Validate open_trade_count matches open_trade_list length
            if self.open_trade_count != len(self.open_trade_list):
                strategy_logger.warning(f"{self.name}: MISMATCH! open_trade_count={self.open_trade_count} but open_trade_list has {len(self.open_trade_list)} items. Fixing...")
                self.open_trade_count = len(self.open_trade_list)

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

            # Check CME trading hours if enabled
            if self.use_trading_hours and self.trading_hours:
                current_date = index.date()

                # Reset flatten flag on new trading day
                if self._last_flatten_date != current_date:
                    self._positions_flattened_today = False

                # Check if we should flatten positions (20 min before close)
                if self.trading_hours.should_flatten_positions(index):
                    if not self._positions_flattened_today and self.open_trade_count > 0:
                        self.flatten_all_positions("CME daily close approaching")
                        self._positions_flattened_today = True
                        self._last_flatten_date = current_date
                    # Don't enter new trades during flatten window
                    self.check_trade_to_remove()
                    self.save_state()
                    return

                # Check if market is closed
                if not self.trading_hours.is_trading_allowed(index):
                    # Still check for exits on existing trades but don't enter new ones
                    self.check_trade_to_remove()
                    self.save_state()
                    return

            # Normal trading logic
            if self.is_trading_long:
                self.run_buy_strategy()
            else:
                self.run_sell_strategy()

            self.check_trade_to_remove()

            # Save state after each update
            self.save_state()

    def print_trade_stats(self):
        # Print Trade Summary
        logger = logging.getLogger(__name__)
        logger.info(f"Total Pnl for {self.name}: ${self.total_pnl}")

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

        # Calculate longest losing streak
        current_streak = 0
        for trade in self.trade_history:
            if trade[1] == 'EXIT':
                if trade[3] <= 0:
                    current_streak += 1
                    self.max_losing_streak = max(self.max_losing_streak, current_streak)
                else:
                    current_streak = 0

        logger.info(f"\n{self.name} | Trade Statistics:")
        logger.info(f"Win %: {win_percentage:.2f}%, Lose %: {lose_percentage:.2f}%")
        logger.info(f"Biggest Winner: {biggest_winner:.2f}")
        logger.info(f"Biggest Loser: {biggest_loser:.2f}")
        logger.info(f"Average Winner: {average_winner:.2f}")
        logger.info(f"Average Loser: {average_loser:.2f}")
        logger.info(f"Total PnL: {self.total_pnl:.2f}")
        logger.info(f"Total Trade made: {self.total_trade}")
        logger.info(f"Highest consecutive lose: {self.max_losing_streak}")

    def plot_trades(self, instrument_data):

        # Plot Price and Trade Entries
        plt.figure(figsize=(10, 5))
        plt.plot(instrument_data.index, instrument_data['close'], label='Price', color='black')

        plt.scatter(instrument_data.index, instrument_data['close'], color='blue', s=5, label='Close Price Dots')
        for trade in self.trade_history:
            if trade[1] == "EXIT":
                continue
            color = 'g' if trade[1] == 'BUY' else 'r'
            plt.scatter(trade[0], trade[2], color=color)

        # Add horizontal lines for static levels
        for level in self.static_levels:
            plt.axhline(y=level, color='black', linestyle='--', linewidth=0.5)
                
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
