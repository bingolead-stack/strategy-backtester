"""
Logging configuration for the trading bot.
Sets up rotating file handlers to keep logs organized and manageable.
"""
import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime

def setup_logging(log_dir="logs", log_level=logging.DEBUG):
    """
    Set up comprehensive logging for the trading bot.
    
    Creates separate log files for:
    - Main application logs
    - Strategy execution logs  
    - Database operations logs
    - Trade execution logs
    
    Args:
        log_dir: Directory to store log files
        log_level: Logging level (default: DEBUG)
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler - only show INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Main application log file - rotating by size (10MB per file, keep 5 backups)
    main_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'trading_bot.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_file_handler.setLevel(logging.DEBUG)
    main_file_handler.setFormatter(detailed_formatter)
    
    # Strategy execution log - rotating by size
    strategy_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'strategy.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    strategy_file_handler.setLevel(logging.DEBUG)
    strategy_file_handler.setFormatter(detailed_formatter)
    
    # Database operations log - rotating by size
    db_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'database.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    db_file_handler.setLevel(logging.DEBUG)
    db_file_handler.setFormatter(detailed_formatter)
    
    # Trade execution log - daily rotation (keep 30 days)
    trade_file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, 'trades.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    trade_file_handler.setLevel(logging.INFO)
    trade_file_handler.setFormatter(detailed_formatter)
    trade_file_handler.suffix = '%Y-%m-%d'
    
    # Debug log - everything, rotating by size
    debug_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'debug.log'),
        maxBytes=20*1024*1024,  # 20MB
        backupCount=3,
        encoding='utf-8'
    )
    debug_file_handler.setLevel(logging.DEBUG)
    debug_file_handler.setFormatter(detailed_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(main_file_handler)
    root_logger.addHandler(debug_file_handler)
    
    # Configure specific loggers
    
    # Strategy logger
    strategy_logger = logging.getLogger('strategy')
    strategy_logger.addHandler(strategy_file_handler)
    strategy_logger.setLevel(logging.DEBUG)
    
    # Database logger
    db_logger = logging.getLogger('database')
    db_logger.addHandler(db_file_handler)
    db_logger.setLevel(logging.DEBUG)
    
    # Trade logger
    trade_logger = logging.getLogger('trades')
    trade_logger.addHandler(trade_file_handler)
    trade_logger.setLevel(logging.INFO)
    
    # Prevent propagation to root for specialized loggers
    strategy_logger.propagate = True  # Also log to main
    db_logger.propagate = True  # Also log to main
    trade_logger.propagate = True  # Also log to main
    
    # Log startup message
    root_logger.info("="*80)
    root_logger.info(f"Logging system initialized - Session started at {datetime.now()}")
    root_logger.info(f"Log directory: {os.path.abspath(log_dir)}")
    root_logger.info(f"Log level: {logging.getLevelName(log_level)}")
    root_logger.info("="*80)
    
    return root_logger


def get_logger(name):
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (e.g., 'strategy', 'database', 'trades')
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

