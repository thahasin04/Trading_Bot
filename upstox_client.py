import os, requests

BASE = os.getenv("UPSTOX_BASE_URL", "https://api-v2.upstox.com").rstrip("/")

def get_token():
    if os.path.exists("access_token.txt"):
        return open("access_token.txt").read().strip()
    return None

def headers():
    token = get_token()
    if not token:
        raise Exception("No access token. Please login first.")
    return {"Authorization": f"Bearer {token}"}

def _get(path, params=None):
    url = BASE + path
    r = requests.get(url, headers=headers(), params=params, timeout=20)
    if r.status_code == 401:
        from app import refresh_access_token
        refresh_access_token()
        r = requests.get(url, headers=headers(), params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def _post(path, data):
    url = BASE + path
    r = requests.post(url, headers=headers(), json=data, timeout=20)
    if r.status_code == 401:
        from app import refresh_access_token
        refresh_access_token()
        r = requests.post(url, headers=headers(), json=data, timeout=20)
    r.raise_for_status()
    return r.json()

# ---- Core APIs ----
def get_profile(): return _get("/user/profile")
def get_funds(): return _get("/user/get-funds-and-margin")
def get_positions(): return _get("/portfolio/positions")
def get_holdings(): return _get("/portfolio/holdings")
def get_orders(): return _get("/order/orders")
def get_trades(): return _get("/order/trades")

# ---- Trading ----
def place_order(symbol, qty, side, order_type="MARKET", product="I", exchange="NSE_EQ"):
    data = {
        "transaction_type": side.upper(),  # BUY / SELL
        "quantity": qty,
        "product": product,
        "order_type": order_type,
        "price": 0,
        "instrument_key": f"{exchange}|{symbol}",
        "disclosed_quantity": 0,
        "validity": "DAY",
        "tag": "trading-bot"
    }
    return _post("/order/place", data)
