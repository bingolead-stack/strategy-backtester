import threading
import requests
import time

def get_access_token():
    url = "https://demo.tradovateapi.com/v1/auth/accesstokenrequest"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "name": "YOUR_USERNAME",
        "password": "YOUR_PASSWORD",
        "appId": "YOUR_APP_ID",
        "appVersion": "1.0",
        "cid": "YOUR_CLIENT_ID",
        "sec": "YOUR_CLIENT_SECRET",
        "deviceId": "my-python-bot"
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()

    data = response.json()
    print(f"[{time.ctime()}] 🔐 Token refreshed.")
    return data['accessToken']

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
                self.token = get_access_token()

    def get_token(self):
        with self.lock:
            return self.token
