import httpx
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

class TradovateTrader:
    def __init__(self, symbol, token_manager):
        self.account_id = None
        self.symbol = symbol
        self.username = os.getenv("TRADOVATE_USERNAME")
        self.api_url = os.getenv("TRADOVATE_API_URL")
        self.token_manager = token_manager

    def ensure_account_id(self):
        if not self.account_id:
            self.find_account_id()
        return self.account_id

    def find_account_id(self):
        access_token = self.token_manager.get_token()
        print("Finding account ID...")
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client() as client:
            res = client.get(f"{self.api_url}/account/list", params={"name": self.symbol}, headers=headers)
            res.raise_for_status()
            accounts = res.json()
            print(f"Found {len(accounts)} accounts.")

            if not accounts:
                raise ValueError("No accounts found.")
            
            self.account_id = accounts[0]["id"]

    def enter_position(self, quantity, is_long):
        if quantity == 0:
            print(f"Quantity is 0. Skipping order.")
            return
        
        self.ensure_account_id()
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

        with httpx.Client() as client:
            res = client.post(f"{self.api_url}/order/placeorder", json=order, headers=headers)
            res.raise_for_status()
            data = res.json()
            print(f"{side} order placed: {data}")
            return data

    def get_current_position(self):
        """Get current position(s) for the account."""
        self.ensure_account_id()
        access_token = self.token_manager.get_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        with httpx.Client() as client:
            res = client.get(f"{self.api_url}/position/list", headers=headers)
            res.raise_for_status()
            positions = res.json()
            
            # Filter positions by account_id
            account_positions = [pos for pos in positions if pos.get("accountId") == self.account_id]
            return account_positions

    def get_net_position(self):
        """Get the net position (netPos) for the current symbol/account.
        Returns 0 if no position exists."""
        positions = self.get_current_position()
        if not positions:
            return 0
        # Return the netPos from the first position (or sum if multiple)
        # Typically there should be one position per account/symbol
        return positions[0].get("netPos", 0)
