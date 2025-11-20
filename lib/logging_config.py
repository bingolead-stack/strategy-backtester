"""
Logging configuration for the trading bot.
Only strategy.log is created - all other logging is disabled.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
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
    
    # Disable ALL logging by default
    logging.disable(logging.CRITICAL)
    
    # Configure root logger - completely silent
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.CRITICAL)
    root_logger.handlers.clear()
    
    # Re-enable only for strategy logger
    logging.disable(logging.NOTSET)
    
    # Configure strategy logger - ONLY logger we use
    strategy_logger = logging.getLogger('strategy')
    strategy_logger.handlers.clear()
    strategy_logger.addHandler(strategy_file_handler)
    strategy_logger.addHandler(console_handler)
    strategy_logger.setLevel(logging.INFO)
    strategy_logger.propagate = False
    
    # Completely silence all other loggers - prevent file creation
    silence_loggers = [
        'database', 'trades', 'uvicorn', 'uvicorn.access', 'uvicorn.error',
        'fastapi', 'asyncio', 'websockets', 'httpx', 'httpcore'
    ]
    for logger_name in silence_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.CRITICAL)
        logger.handlers.clear()
        logger.propagate = False
        logger.disabled = True
    
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

