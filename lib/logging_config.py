"""
Logging configuration for the trading bot.
Sets up rotating file handlers to keep logs organized and manageable.
"""
import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime

def setup_logging(log_dir="logs", log_level=logging.INFO):
    """
    Set up minimal logging - only strategy execution.
    
    Args:
        log_dir: Directory to store log files
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Strategy log file - rotating by size (5MB per file, keep 3 backups)
    strategy_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'strategy.log'),
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    strategy_file_handler.setLevel(logging.INFO)
    strategy_file_handler.setFormatter(formatter)
    
    # Configure root logger - only errors
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.ERROR)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    
    # Configure strategy logger - ONLY logger we use
    strategy_logger = logging.getLogger('strategy')
    strategy_logger.handlers.clear()
    strategy_logger.addHandler(strategy_file_handler)
    strategy_logger.addHandler(console_handler)
    strategy_logger.setLevel(logging.INFO)
    strategy_logger.propagate = False
    
    # Silence all other loggers
    for logger_name in ['database', 'trades', 'uvicorn', 'uvicorn.access', 'uvicorn.error']:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        logging.getLogger(logger_name).handlers.clear()
    
    # Log startup message
    strategy_logger.info("="*80)
    strategy_logger.info(f"Trading Bot Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    strategy_logger.info("="*80)
    
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

