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

def get_access_token():
    print("Requesting initial access token...")
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
        
        res.raise_for_status()
        data = res.json()
        access_token = data["accessToken"]
        # md_access_token = data["mdAccessToken"]
        # token_expiration = datetime.datetime.fromisoformat(data["expirationTime"].replace("Z", "+00:00"))
        # print(f"Token received. Expires at {token_expiration.isoformat()}")
        return access_token

def renew_access_token(token: str):
    print("Attempting to renew access token...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    with httpx.Client() as client:
        res = client.get(f"{TRADOVATE_API_URL}/auth/renewaccesstoken", headers=headers)
        res.raise_for_status()
        data = res.json()
        access_token = data["accessToken"]
        # md_access_token = data["mdAccessToken"]
        # token_expiration = datetime.datetime.fromisoformat(data["expirationTime"].replace("Z", "+00:00"))
        # print(f"Access token renewed. New expiration: {token_expiration.isoformat()}")
        return access_token


class TokenManager:
    def __init__(self, refresh_interval=80 * 60):
        self.token = None
        self.refresh_interval = refresh_interval
        self.lock = threading.Lock()

    def start(self):
        self.token = get_access_token()
        thread = threading.Thread(target=self._refresh_token_loop, daemon=True)
        thread.start()

    def _refresh_token_loop(self):
        while True:
            time.sleep(self.refresh_interval)
            with self.lock:
                self.token = renew_access_token(self.token)

    def get_token(self):
        with self.lock:
            return self.token
