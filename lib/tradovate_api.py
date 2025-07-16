import httpx
from dotenv import load_dotenv
import os
from lib.token_manager import TokenManager

# Load environment variables
load_dotenv()

class TradovateTrader:
    def __init__(self, symbol, token_manager):
        self.account_id = None
        self.symbol = symbol
        self.username = os.getenv("TRADOVATE_USERNAME")
        self.api_url = os.getenv("TRADOVATE_API_URL")
        self.token_manager = token_manager

    async def ensure_account_id(self):
        if not self.account_id:
            await self.find_account_id()
        return self.account_id

    async def find_account_id(self):
        access_token = self.token_manager.get_token()
        print("Finding account ID...")
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.api_url}/account/list", params={"name": self.symbol}, headers=headers)
            res.raise_for_status()
            accounts = res.json()
            print(f"Found {len(accounts)} accounts.")

            if not accounts:
                raise ValueError("No accounts found.")
            
            self.account_id = accounts[0]["id"]

    async def enter_position(self, quantity, is_long):
        await self.ensure_account_id()
        side = "Buy" if is_long else "Sell"

        order = {
            "accountSpec": self.username,
            "accountId": self.account_id,
            "action": side,
            "symbol": self.symbol,
            "orderQty": quantity,
            "orderType": "Market",
            "isAutomated": True
        }

        access_token = self.token_manager.get_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(f"{self.api_url}/order/placeorder", json=order, headers=headers)
            res.raise_for_status()
            data = res.json()
            print(f"{side} order placed: {data}")
            return data
