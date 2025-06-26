import threading
import httpx
import time
from dotenv import load_dotenv
import os

load_dotenv()

TRADOVATE_API_URL = os.getenv("TRADOVATE_API_URL")
TRADOVATE_USERNAME = os.getenv("TRADOVATE_USERNAME")
TRADOVATE_PASSWORD = os.getenv("TRADOVATE_PASSWORD")
TRADOVATE_CLIENT_ID = os.getenv("TRADOVATE_CLIENT_ID")
TRADOVATE_CID = os.getenv("TRADOVATE_CID")
TRADOVATE_SECRET = os.getenv("TRADOVATE_SECRET")

class TokenManager:
    def __init__(self, refresh_interval=30 * 60):
        print("[DEBUG] Initializing TokenManager...")
        self.token = None
        self.refresh_interval = refresh_interval
        self.lock = threading.Lock()

    def start(self):
        print("[DEBUG] Starting token manager...")
        self.token = self.get_access_token()
        print("[DEBUG] Starting refresh token thread...")
        thread = threading.Thread(target=self._refresh_token_loop, daemon=True)
        thread.start()

    def _refresh_token_loop(self):
        while True:
            print(f"[DEBUG] Sleeping for {self.refresh_interval} seconds before token renewal...")
            time.sleep(self.refresh_interval)
            with self.lock:
                try:
                    self.token = self.renew_access_token(self.token)
                    print("[DEBUG] Token successfully renewed inside loop.")
                except Exception as e:
                    print(f"[ERROR] Failed to renew access token: {e}")

    def get_token(self):
        with self.lock:
            print("[DEBUG] Fetching current access token...")
            return self.token
        
    def get_access_token(self):
        print("[DEBUG] Requesting initial access token...")
        with httpx.Client() as client:
            res = client.post(f"{TRADOVATE_API_URL}/auth/accesstokenrequest", 
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                },
                json={
                    "name": TRADOVATE_USERNAME,
                    "password": TRADOVATE_PASSWORD,
                    "appId": TRADOVATE_CLIENT_ID,
                    "appVersion": "0.0.1",
                    "cid": TRADOVATE_CID,
                    "sec": TRADOVATE_SECRET
                })

            print(f"[DEBUG] Status Code: {res.status_code}")
            res.raise_for_status()
            data = res.json()
            access_token = data["accessToken"]
            print("[DEBUG] Access token obtained successfully.")
            return access_token

    def renew_access_token(self, token: str):
        print("[DEBUG] Attempting to renew access token...")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        with httpx.Client() as client:
            res = client.get(f"{TRADOVATE_API_URL}/auth/renewaccesstoken", headers=headers)
            print(f"[DEBUG] Status Code (renew): {res.status_code}")
            res.raise_for_status()
            data = res.json()
            access_token = data["accessToken"]
            print("[DEBUG] Access token renewed successfully.")
            return access_token