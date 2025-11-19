import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading

# Use the database logger configured in logging_config
db_logger = logging.getLogger('database')

class StatePersistence:
    """
    Manages SQLite persistence for trading strategy state.
    Saves all internal state including trading history, open trades, and static level crossings.
    """
    
    def __init__(self, db_path: str = "strategy_state.db"):
        """
        Initialize the state persistence manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Table for strategy state
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS strategy_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT UNIQUE NOT NULL,
                    current_cash_value REAL,
                    open_trade_count INTEGER,
                    total_pnl REAL,
                    price REAL,
                    last_price REAL,
                    high_price REAL,
                    low_price REAL,
                    last_index TEXT,
                    winrate REAL,
                    avg_winner REAL,
                    avg_loser REAL,
                    total_trade INTEGER,
                    reward_to_risk REAL,
                    max_losing_streak INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Table for trade history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    trade_index TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    pnl REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_name) REFERENCES strategy_state(strategy_name)
                )
            ''')
            
            # Table for open trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS open_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    trade_time TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_level REAL NOT NULL,
                    trailing_stop REAL,
                    traded_level REAL NOT NULL,
                    take_profit_level REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_name) REFERENCES strategy_state(strategy_name)
                )
            ''')
            
            # Table for retrace levels
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS retrace_levels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    level_index INTEGER NOT NULL,
                    direction TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_name) REFERENCES strategy_state(strategy_name),
                    UNIQUE(strategy_name, level_index)
                )
            ''')
            
            # Table for cumulative PnL
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cumulative_pnl (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL,
                    pnl_value REAL NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_name) REFERENCES strategy_state(strategy_name)
                )
            ''')
            
            # Table for static levels (for reference)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS static_levels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    level_value REAL NOT NULL,
                    level_index INTEGER NOT NULL,
                    FOREIGN KEY (strategy_name) REFERENCES strategy_state(strategy_name),
                    UNIQUE(strategy_name, level_index)
                )
            ''')
            
            conn.commit()
            conn.close()
            db_logger.info(f"Database initialized at {self.db_path}")
    
    def save_strategy_state(self, strategy_name: str, state: Dict[str, Any]):
        """
        Save complete strategy state to database.
        
        Args:
            strategy_name: Unique name for the strategy
            state: Dictionary containing all strategy state
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Save main strategy state
                cursor.execute('''
                    INSERT OR REPLACE INTO strategy_state 
                    (strategy_name, current_cash_value, open_trade_count, total_pnl,
                     price, last_price, high_price, low_price, last_index,
                     winrate, avg_winner, avg_loser, total_trade, reward_to_risk,
                     max_losing_streak, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    strategy_name,
                    state.get('current_cash_value', 0),
                    state.get('open_trade_count', 0),
                    state.get('total_pnl', 0),
                    state.get('price'),
                    state.get('last_price'),
                    state.get('high_price'),
                    state.get('low_price'),
                    str(state.get('index', '')),
                    state.get('winrate', 0),
                    state.get('avg_winner', 0),
                    state.get('avg_loser', 0),
                    state.get('total_trade', 0),
                    state.get('reward_to_risk', 0),
                    state.get('max_losing_streak', 0)
                ))
                
                # Save trade history (clear and reinsert to avoid duplicates)
                # Only save new trades by checking what's already in DB
                cursor.execute('''
                    SELECT COUNT(*) FROM trade_history WHERE strategy_name = ?
                ''', (strategy_name,))
                existing_count = cursor.fetchone()[0]
                
                trade_history = state.get('trade_history', [])
                new_trades = trade_history[existing_count:]
                
                for trade in new_trades:
                    cursor.execute('''
                        INSERT INTO trade_history 
                        (strategy_name, trade_index, trade_type, price, pnl)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (strategy_name, str(trade[0]), trade[1], trade[2], trade[3]))
                
                # Save open trades (clear and reinsert)
                cursor.execute('DELETE FROM open_trades WHERE strategy_name = ?', (strategy_name,))
                for trade in state.get('open_trade_list', []):
                    cursor.execute('''
                        INSERT INTO open_trades 
                        (strategy_name, trade_time, entry_price, stop_level, 
                         trailing_stop, traded_level, take_profit_level)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (strategy_name, str(trade[0]), trade[1], trade[2], 
                          trade[3], trade[4], trade[5]))
                
                # Save retrace levels (update or insert)
                for level_idx, direction in state.get('retrace_levels', {}).items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO retrace_levels 
                        (strategy_name, level_index, direction)
                        VALUES (?, ?, ?)
                    ''', (strategy_name, level_idx, direction))
                
                # Save cumulative PnL (only new values)
                cursor.execute('''
                    SELECT COUNT(*) FROM cumulative_pnl WHERE strategy_name = ?
                ''', (strategy_name,))
                existing_pnl_count = cursor.fetchone()[0]
                
                cumulative_pnl = state.get('cumulative_pnl', [])
                new_pnl_values = cumulative_pnl[existing_pnl_count:]
                
                for idx, pnl_value in enumerate(new_pnl_values, start=existing_pnl_count):
                    cursor.execute('''
                        INSERT INTO cumulative_pnl 
                        (strategy_name, sequence_number, pnl_value)
                        VALUES (?, ?, ?)
                    ''', (strategy_name, idx, pnl_value))
                
                # Save static levels if provided (only once)
                if state.get('static_levels'):
                    cursor.execute('''
                        SELECT COUNT(*) FROM static_levels WHERE strategy_name = ?
                    ''', (strategy_name,))
                    if cursor.fetchone()[0] == 0:
                        for idx, level in enumerate(state['static_levels']):
                            cursor.execute('''
                                INSERT INTO static_levels 
                                (strategy_name, level_value, level_index)
                                VALUES (?, ?, ?)
                            ''', (strategy_name, level, idx))
                
                conn.commit()
                db_logger.info(f"Successfully saved state to DB for strategy: {strategy_name}")
                db_logger.debug(f"  - Saved {len(new_trades)} new trades (total history: {len(trade_history)})")
                db_logger.debug(f"  - Saved {len(state.get('open_trade_list', []))} open trades")
                db_logger.debug(f"  - Saved {len(new_pnl_values)} new PnL values")
                db_logger.debug(f"  - Saved {len([v for v in state.get('retrace_levels', {}).values() if v is not None])} active retrace levels")
                
            except Exception as e:
                conn.rollback()
                db_logger.error(f"Failed to save strategy state to DB for {strategy_name}: {e}", exc_info=True)
                raise
            finally:
                conn.close()
    
    def load_strategy_state(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        Load complete strategy state from database.
        
        Args:
            strategy_name: Unique name for the strategy
            
        Returns:
            Dictionary containing all strategy state, or None if not found
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # Load main strategy state
                cursor.execute('''
                    SELECT current_cash_value, open_trade_count, total_pnl,
                           price, last_price, high_price, low_price, last_index,
                           winrate, avg_winner, avg_loser, total_trade, 
                           reward_to_risk, max_losing_streak
                    FROM strategy_state WHERE strategy_name = ?
                ''', (strategy_name,))
                
                row = cursor.fetchone()
                if not row:
                    db_logger.info(f"No saved state found for strategy: {strategy_name}")
                    return None
                
                state = {
                    'current_cash_value': row[0],
                    'open_trade_count': row[1],
                    'total_pnl': row[2],
                    'price': row[3],
                    'last_price': row[4],
                    'high_price': row[5],
                    'low_price': row[6],
                    'index': row[7],
                    'winrate': row[8],
                    'avg_winner': row[9],
                    'avg_loser': row[10],
                    'total_trade': row[11],
                    'reward_to_risk': row[12],
                    'max_losing_streak': row[13]
                }
                
                # Load trade history
                cursor.execute('''
                    SELECT trade_index, trade_type, price, pnl
                    FROM trade_history 
                    WHERE strategy_name = ?
                    ORDER BY id
                ''', (strategy_name,))
                
                state['trade_history'] = []
                for trade_row in cursor.fetchall():
                    state['trade_history'].append((
                        trade_row[0],  # Keep as string, will be converted as needed
                        trade_row[1],
                        trade_row[2],
                        trade_row[3]
                    ))
                
                # Load open trades
                cursor.execute('''
                    SELECT trade_time, entry_price, stop_level, trailing_stop,
                           traded_level, take_profit_level
                    FROM open_trades 
                    WHERE strategy_name = ?
                    ORDER BY id
                ''', (strategy_name,))
                
                state['open_trade_list'] = []
                for trade_row in cursor.fetchall():
                    state['open_trade_list'].append([
                        trade_row[0],  # Keep as string
                        trade_row[1],
                        trade_row[2],
                        trade_row[3],
                        trade_row[4],
                        trade_row[5]
                    ])
                
                # Load retrace levels
                cursor.execute('''
                    SELECT level_index, direction
                    FROM retrace_levels 
                    WHERE strategy_name = ?
                    ORDER BY level_index
                ''', (strategy_name,))
                
                state['retrace_levels'] = {}
                for level_row in cursor.fetchall():
                    state['retrace_levels'][level_row[0]] = level_row[1]  # direction: 'up', 'down', or None
                
                # Load cumulative PnL
                cursor.execute('''
                    SELECT pnl_value
                    FROM cumulative_pnl 
                    WHERE strategy_name = ?
                    ORDER BY sequence_number
                ''', (strategy_name,))
                
                state['cumulative_pnl'] = [row[0] for row in cursor.fetchall()]
                
                # Load static levels
                cursor.execute('''
                    SELECT level_value
                    FROM static_levels 
                    WHERE strategy_name = ?
                    ORDER BY level_index
                ''', (strategy_name,))
                
                state['static_levels'] = [row[0] for row in cursor.fetchall()]
                
                db_logger.info(f"Successfully loaded state from DB for strategy: {strategy_name}")
                db_logger.debug(f"  - Loaded {len(state['trade_history'])} trades from history")
                db_logger.debug(f"  - Loaded {len(state['open_trade_list'])} open trades")
                db_logger.debug(f"  - Loaded {len(state['cumulative_pnl'])} PnL values")
                db_logger.debug(f"  - Loaded {len([v for v in state['retrace_levels'].values() if v is not None])} active retrace levels")
                db_logger.debug(f"  - Total PnL: {state['total_pnl']}")
                db_logger.debug(f"  - Open trade count: {state['open_trade_count']}")
                return state
                
            except Exception as e:
                db_logger.error(f"Failed to load strategy state from DB for {strategy_name}: {e}", exc_info=True)
                raise
            finally:
                conn.close()
    
    def delete_strategy_state(self, strategy_name: str):
        """
        Delete all state for a strategy from the database.
        
        Args:
            strategy_name: Unique name for the strategy
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('DELETE FROM trade_history WHERE strategy_name = ?', (strategy_name,))
                cursor.execute('DELETE FROM open_trades WHERE strategy_name = ?', (strategy_name,))
                cursor.execute('DELETE FROM retrace_levels WHERE strategy_name = ?', (strategy_name,))
                cursor.execute('DELETE FROM cumulative_pnl WHERE strategy_name = ?', (strategy_name,))
                cursor.execute('DELETE FROM static_levels WHERE strategy_name = ?', (strategy_name,))
                cursor.execute('DELETE FROM strategy_state WHERE strategy_name = ?', (strategy_name,))
                
                conn.commit()
                db_logger.info(f"Deleted state for strategy: {strategy_name}")
                
            except Exception as e:
                conn.rollback()
                db_logger.error(f"Error deleting strategy state for {strategy_name}: {e}", exc_info=True)
                raise
            finally:
                conn.close()
    
    def list_strategies(self) -> List[str]:
        """
        List all strategy names stored in the database.
        
        Returns:
            List of strategy names
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT strategy_name FROM strategy_state')
                return [row[0] for row in cursor.fetchall()]
            finally:
                conn.close()
    
    def get_last_update_time(self, strategy_name: str) -> Optional[str]:
        """
        Get the last update timestamp for a strategy.
        
        Args:
            strategy_name: Unique name for the strategy
            
        Returns:
            Timestamp string or None if not found
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    SELECT last_updated 
                    FROM strategy_state 
                    WHERE strategy_name = ?
                ''', (strategy_name,))
                
                row = cursor.fetchone()
                return row[0] if row else None
            finally:
                conn.close()
