from fastapi import FastAPI, HTTPException
from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from datetime import datetime
import uvicorn
import logging

from lib.tradovate_api import TradovateTrader
from strategy.strategy import Strategy

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
trader = TradovateTrader()
strategy1 = Strategy(
    name="High PNL Strategy",
    trader=trader,
    entry_offset=100,
    take_profit_offset=12800,
    stop_loss_offset=200,
    trail_trigger=5,
    re_entry_distance=1,
    max_open_trades=10,
    max_contracts_per_trade=1
)
strategy1.load_static_levels(STATIC_LEVELS)

strategy2 = Strategy(
    name="High Win Rate Strategy",
    trader=trader,
    entry_offset=10,
    take_profit_offset=25,
    stop_loss_offset=200,
    trail_trigger=5,
    re_entry_distance=1,
    max_open_trades=10,
    max_contracts_per_trade=1
)
strategy2.load_static_levels(STATIC_LEVELS)

strategy3 = Strategy(
    name="Balanced Strategy",
    trader=trader,
    entry_offset=100,
    take_profit_offset=25600,
    stop_loss_offset=200,
    trail_trigger=2,
    re_entry_distance=2,
    max_open_trades=10,
    max_contracts_per_trade=1
)
strategy3.load_static_levels(STATIC_LEVELS)

last_price = None

app = FastAPI()

class Signal(BaseModel):
    open: float
    high: float
    low: float
    close: float

@app.post("/webhook")
async def receive_signal(signal: Signal):
    global last_price, strategy1, strategy2, strategy3
    if strategy1 is None:
        logger.error("Strategy not initialized")
        raise HTTPException(status_code=500, detail="Strategy not initialized")

    logger.info(f"Received signal: {signal}")
    if last_price is None:
        last_price = signal.close
        return {"status": "success"}
    
    strategy1.update(datetime.now(), last_price, signal.close, signal.high, signal.low)
    last_price = signal.close
    return {"status": "success"}

if __name__ == "__main__":
    logger.info("Starting FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
