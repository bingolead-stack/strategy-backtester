from fastapi import FastAPI, HTTPException
from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from datetime import datetime
import uvicorn
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os

load_dotenv()

from lib.token_manager import TokenManager
from lib.tradovate_api import TradovateTrader
from lib.state_persistence import StatePersistence
from strategy.strategy import Strategy
from lib.logging_config import setup_logging

# Set up logging
setup_logging(log_dir="logs", log_level=logging.DEBUG)
logger = logging.getLogger(__name__)

IS_TRADING_LONG = os.getenv("IS_LONG_ONLY_TRADE")
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
    7870, 7928.5, 7987, 8045.5, 8104, 8162.5, 8221, 8279.5, 8338, 8396.5,
    8455, 8513.5, 8572, 8630.5, 8689, 8747.5, 8806, 8864.5, 8923, 8981.5,
    9040, 9098.5, 9157, 9215.5, 9274, 9332.5, 9391, 9449.5, 9508, 9566.5,
    9625, 9683.5, 9742, 9800.5, 9859, 9917.5, 9976, 10034.5, 10093, 10151.5,
    10210, 10268.5, 10327, 10385.5, 10444, 10502.5, 10561, 10619.5, 10678,
    10736.5, 10795, 10853.5, 10912, 10970.5, 11029, 11087.5, 11146, 11204.5,
    11263, 11321.5, 11380, 11438.5, 11497, 11555.5, 11614, 11672.5, 11731,
    11789.5, 11848, 11906.5, 11965, 12023.5, 12082, 12140.5, 12199, 12257.5,
    12316, 12374.5, 12433, 12491.5, 12550, 12608.5, 12667, 12725.5, 12784,
    12842.5, 12901, 12959.5, 13018, 13076.5, 13135, 13193.5, 13252, 13310.5,
    13369, 13427.5, 13486, 13544.5, 13603, 13661.5, 13720, 13778.5, 13837,
    13895.5, 13954, 14012.5, 14071, 14129.5, 14188, 14246.5, 14305, 14363.5,
    14422, 14480.5, 14539, 14597.5, 14656, 14714.5, 14773, 14831.5, 14890,
    14948.5, 15007, 15065.5, 15124, 15182.5, 15241, 15299.5, 15358, 15416.5,
    15475, 15533.5, 15592, 15650.5, 15709, 15767.5, 15826, 15884.5, 15943,
    16001.5, 16060, 16118.5, 16177, 16235.5, 16294, 16352.5, 16411, 16469.5,
    16528, 16586.5, 16645, 16703.5, 16762, 16820.5, 16879, 16937.5, 16996,
    17054.5, 17113, 17171.5, 17230, 17288.5, 17347, 17405.5, 17464, 17522.5,
    17581, 17639.5, 17698, 17756.5, 17815, 17873.5, 17932, 17990.5, 18049,
    18107.5, 18166, 18224.5, 18283, 18341.5, 18400, 18458.5, 18517, 18575.5,
    18634, 18692.5, 18751, 18809.5, 18868, 18926.5, 18985, 19043.5, 19102,
    19160.5, 19219, 19277.5, 19336, 19394.5, 19453, 19511.5, 19570, 19628.5,
    19687, 19745.5, 19804, 19862.5, 19921, 19979.5, 20038
]
token_manager = None
swing_strategy_long = None
swing_strategy_short = None
swing_trader = None
scalp_strategy_long = None
scalp_strategy_short = None
scalp_trader = None
state_persistence = None

high_pnl_strategy = None

last_price = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global swing_strategy_long, swing_strategy_short, swing_trader, scalp_strategy_long, scalp_strategy_short, scalp_trader, high_pnl_strategy, token_manager, state_persistence
    # Startup
    logger.info("Startup: initializing resources...")

    # Initialize state persistence
    state_persistence = StatePersistence(db_path="trading_bot_state.db")
    logger.info("State persistence initialized")

    token_manager = TokenManager()
    token_manager.start()
    swing_trader = TradovateTrader(symbol="ESH6", token_manager=token_manager)
    
    # Create strategies with persistence enabled
    swing_strategy_long = Strategy(
        name="Swing Long Strategy",
        trader=swing_trader,
        entry_offset=100,
        take_profit_offset=500,
        stop_loss_offset=150,
        trail_trigger=10,
        re_entry_distance=1,
        max_open_trades=1,
        max_contracts_per_trade=1,
        symbol_size=50,
        is_trading_long=True,
        persistence=state_persistence,
        auto_save=True
    )
    swing_strategy_short = Strategy(
        name="Swing Short Strategy",
        trader=swing_trader,
        entry_offset=15,
        take_profit_offset=800,
        stop_loss_offset=200,
        trail_trigger=10,
        re_entry_distance=1,
        max_open_trades=1,
        max_contracts_per_trade=1,
        symbol_size=5,
        is_trading_long=False,
        persistence=state_persistence,
        auto_save=True
    )
    
    # Load static levels first
    swing_strategy_long.load_static_levels(STATIC_LEVELS)
    swing_strategy_short.load_static_levels(STATIC_LEVELS)
    
    high_pnl_trader = TradovateTrader(symbol="MESH6", token_manager=token_manager)
    high_pnl_strategy = Strategy(
        name="High PNL Strategy",
        trader=high_pnl_trader,
        entry_offset=10,
        take_profit_offset=2925,
        stop_loss_offset=150,
        trail_trigger=10,
        re_entry_distance=1,
        max_open_trades=10,
        max_contracts_per_trade=1,
        symbol_size=50,
        is_trading_long=True,
        persistence=state_persistence,
        auto_save=True
    )
    high_pnl_strategy.load_static_levels(STATIC_LEVELS)
    # Try to load saved state
    swing_strategy_long.load_state()
    swing_strategy_short.load_state()
    high_pnl_strategy.load_state()

    # scalp_trader = TradovateTrader(symbol="ESZ5", token_manager=token_manager)
    # scalp_strategy_long = Strategy(
    #     name="Scalp Long Strategy",
    #     trader=scalp_trader,
    #     entry_offset=5,
    #     take_profit_offset=35,
    #     stop_loss_offset=100,
    #     trail_trigger=10,
    #     re_entry_distance=1,
    #     max_open_trades=10,
    #     max_contracts_per_trade=1,
    #     symbol_size=50,
    #     is_trading_long=True,
    #     persistence=state_persistence,
    #     auto_save=True
    # )
    # scalp_strategy_short = Strategy(
    #     name="Scalp Short Strategy",
    #     trader=scalp_trader,
    #     entry_offset=10,
    #     take_profit_offset=20,
    #     stop_loss_offset=150,
    #     trail_trigger=10,
    #     re_entry_distance=1,
    #     max_open_trades=10,
    #     max_contracts_per_trade=1,
    #     symbol_size=50,
    #     is_trading_long=False,
    #     persistence=state_persistence,
    #     auto_save=True
    # )
    
    # Load static levels first
    # scalp_strategy_long.load_static_levels(STATIC_LEVELS)
    # scalp_strategy_short.load_static_levels(STATIC_LEVELS)
    
    # Try to load saved state
    # if scalp_strategy_long.load_state():
    #     logger.info("Scalp Long Strategy: Restored from saved state")
    # else:
    #     logger.info("Scalp Long Strategy: Starting fresh")
    
    # if scalp_strategy_short.load_state():
    #     logger.info("Scalp Short Strategy: Restored from saved state")
    # else:
    #     logger.info("Scalp Short Strategy: Starting fresh")

    yield
    # Shutdown
    logger.info("="*80)
    logger.info("Shutdown - Saving state and printing results")
    logger.info("="*80)
    try:
        if IS_TRADING_LONG:
            swing_strategy_long.save_state()
            swing_strategy_long.print_trade_stats()
        else:
            swing_strategy_short.save_state()
            swing_strategy_short.print_trade_stats()

        high_pnl_strategy.save_state()
        high_pnl_strategy.print_trade_stats()
        
        logger.info("="*80)
        logger.info("Shutdown complete")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"Error in shutdown: {e}", exc_info=True)

app = FastAPI(lifespan=lifespan)

class Signal(BaseModel):
    open: float
    high: float
    low: float
    close: float

@app.post("/webhook")
async def receive_signal(signal: Signal):
    global last_price, swing_strategy_long, scalp_strategy_long, swing_strategy_short, scalp_strategy_short, high_pnl_strategy
    if swing_strategy_long is None or swing_strategy_short is None or high_pnl_strategy is None:
        logger.error("Strategy not initialized")
        raise HTTPException(status_code=500, detail="Strategy not initialized")
    
    if last_price is None:
        last_price = signal.close
        return {"status": "success"}
    
    if IS_TRADING_LONG:
        swing_strategy_long.update(datetime.now(), signal.close, last_price, signal.high, signal.low)
        # scalp_strategy_long.update(datetime.now(), signal.close, last_price, signal.high, signal.low)
    else:
        swing_strategy_short.update(datetime.now(), signal.close, last_price, signal.high, signal.low)
        # scalp_strategy_short.update(datetime.now(), signal.close, last_price, signal.high, signal.low)

    high_pnl_strategy.update(datetime.now(), signal.close, last_price, signal.high, signal.low)

    last_price = signal.close
    return {"status": "success"}

if __name__ == "__main__":
    logger.info("Starting FastAPI application...")
    uvicorn.run("main:app", host="0.0.0.0", port=80)
