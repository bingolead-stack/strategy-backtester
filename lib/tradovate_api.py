import httpx
import datetime
import asyncio
from dotenv import load_dotenv
import os

from lib.token_manager import TokenManager

# Load the .env file
load_dotenv()
account_id = None

TRADOVATE_USERNAME = os.getenv("TRADOVATE_USERNAME")
TRADOVATE_API_URL = os.getenv("TRADOVATE_API_URL")

token_manager = TokenManager()
token_manager.start()

async def ensure_account_id():
    global account_id
    if not account_id:
        await find_account_id()
    return account_id

async def find_account_id():
    global account_id
    access_token = token_manager.get_token()
    print(f"Finding account id")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{TRADOVATE_API_URL}/account/list", params={"name": "ESM5"}, headers=headers)
        res.raise_for_status()
        accounts = res.json()
        print(f"Found {len(accounts)} accounts.")

        account = accounts[0]
        account_id = account["id"]

async def enter_position(quantity, is_long):
    global account_id
    await ensure_account_id()
    
    side = "Buy" if is_long else "Sell"
    order = {
        "accountSpec": TRADOVATE_USERNAME,
        "accountId": account_id,
        "action": side,
        "symbol": "ESM5",
        "orderQty": quantity,
        "orderType": "Market",
        "isAutomated": True
    }
    access_token = token_manager.get_token()
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{TRADOVATE_API_URL}/order/placeorder", json=order, headers=headers)
        data = res.json()
        print(f"{side} order placed: {data}")
        return data
