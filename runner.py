import websocket
import json
from datetime import datetime
from strategy import Strategy
import pandas as pd

from token_manager import TokenManager

token_manager = TokenManager()
token_manager.start()

access_token = token_manager.get_token()

# ---- Setup Your Strategy Optimized Parameters---- #
LOTS_PER_TRADE = 3
ENTRY_OFFSET = 8
STOP_LOSS_OFFSET = 100
TRAIL_TRIGGER = 2
RE_ENTRY_DISTANCE = 2
MAX_OPEN_TRADES = LOTS_PER_TRADE * 1

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

long_dates = pd.date_range(start="2000-01-01", end=datetime.today(), freq="30min")
short_dates = []

strategy = Strategy(
    name="Paper Strategy",
    entry_offset=ENTRY_OFFSET,
    stop_loss_offset=STOP_LOSS_OFFSET,
    trail_trigger=TRAIL_TRIGGER,
    re_entry_distance=RE_ENTRY_DISTANCE,
    max_open_trades=MAX_OPEN_TRADES,
    max_contracts_per_trade=LOTS_PER_TRADE,
    long_dates=long_dates,
    short_dates=short_dates
)

strategy.load_static_levels(STATIC_LEVELS)

# ---- WebSocket Logic ---- #

def on_message(ws, message):
    try:
        msg = json.loads(message)
        if msg.get("e") == "quote":
            price = msg['bp']  # Best bid
            high_price = msg['h']
            timestamp = pd.Timestamp.now()

            # Provide dummy last_price for now
            last_price = price + 1
            access_token = token_manager.get_token()

            strategy.update(index=timestamp, price=price, last_price=last_price, high_price=high_price, access_token=access_token)
            print(f"[{timestamp}] Updated strategy with price={price}")
    except Exception as e:
        print("Error processing message:", e)

def on_open(ws):
    print("WebSocket opened. Authenticating...")

    # Authenticate
    auth_msg = {
        "msgType": "authorize",
        "token": access_token
    }
    ws.send(json.dumps(auth_msg))

    # Subscribe to quotes
    sub_msg = {
        "msgType": "subscribeQuote",
        "symbol": "ESM5"  # replace with your symbol
    }
    ws.send(json.dumps(sub_msg))
    print("Subscribed to quote for ESM5")

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print(f"WebSocket closed with status code {close_status_code}:", close_msg)

if __name__ == '__main__':
    ws_url = "wss://md-demo.tradovateapi.com/v1/websocket"

    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()
