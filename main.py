from fastapi import FastAPI, Request, HTTPException
from fastapi import FastAPI
from contextlib import asynccontextmanager
from pydantic import BaseModel
import json
import pandas as pd
from datetime import datetime
import uvicorn
import logging

from strategy.strategy import Strategy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

strategy = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global strategy
    logger.info("App startup event triggered")
    with open("app_config.json", "r") as f:
        strategy_config = json.load(f)

    STATIC_LEVELS = strategy_config.get("static_levels", [])
    logger.info("Loaded static levels")

    long_date_ranges = strategy_config.get("long_date_ranges", [])
    long_dates = pd.DatetimeIndex([])
    for start_str, end_str in long_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        long_dates = long_dates.union(pd.date_range(start=start, end=end, freq="30min"))

    short_date_ranges = strategy_config.get("short_date_ranges", [])
    short_dates = pd.DatetimeIndex([])
    for start_str, end_str in short_date_ranges:
        start = pd.to_datetime(start_str)
        end = pd.to_datetime(end_str)
        short_dates = short_dates.union(pd.date_range(start=start, end=end, freq="30min"))

    strategy = Strategy(
        name=strategy_config["name"],
        entry_offset=strategy_config["entry_offset"],
        take_profit_offset=strategy_config["take_profit_offset"],
        stop_loss_offset=strategy_config["stop_loss_offset"],
        trail_trigger=strategy_config["trail_trigger"],
        re_entry_distance=strategy_config["re_entry_distance"],
        max_open_trades=strategy_config["max_open_trades"],
        max_contracts_per_trade=strategy_config["max_contracts_per_trade"],
        long_dates=long_dates,
        short_dates=short_dates
    )
    strategy.load_static_levels(STATIC_LEVELS)
    logger.info("Strategy initialized")

    yield

app = FastAPI(lifespan=lifespan)

class Signal(BaseModel):
    symbol: str
    action: str  # e.g., 'buy' or 'sell'
    timestamp: str  # ISO format timestamp
    price: float


@app.post("/webhook")
async def receive_signal(signal: Signal):
    if strategy is None:
        logger.error("Strategy not initialized")
        raise HTTPException(status_code=500, detail="Strategy not initialized")

    logger.info(f"Received signal: {signal}")

    signal_time = pd.to_datetime(signal.timestamp)
    if signal.action.lower() == 'buy':
        strategy.enter_long(signal.symbol, signal.price, signal_time)
        logger.info(f"Entered long position for {signal.symbol} at {signal.price}")
    elif signal.action.lower() == 'sell':
        strategy.enter_short(signal.symbol, signal.price, signal_time)
        logger.info(f"Entered short position for {signal.symbol} at {signal.price}")
    else:
        logger.error("Unknown action type")
        raise HTTPException(status_code=400, detail="Unknown action type")

    return {"status": "success"}


if __name__ == "__main__":
    logger.info("Starting FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
