import os, time, json, threading
from flask import Flask, render_template, redirect, request, Response
from dotenv import load_dotenv
import requests

# ---- Load ENV ----
load_dotenv()
API_KEY = os.getenv("UPSTOX_API_KEY")
API_SECRET = os.getenv("UPSTOX_API_SECRET")
REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI")
BASE = os.getenv("UPSTOX_BASE_URL", "https://api.upstox.com/v2").rstrip("/")

TOKEN_URL = f"{BASE}/login/authorization/token"
AUTH_DIALOG = f"{BASE}/login/authorization/dialog"
REFRESH_URL = f"{BASE}/login/refresh/token"

# ---- Token Handling ----
def get_token():
    if os.path.exists("access_token.txt"):
        return open("access_token.txt").read().strip()
    return None

def save_token(access_token, refresh_token=None):
    with open("access_token.txt", "w") as f:
        f.write(access_token)
    if refresh_token:
        with open("refresh_token.txt", "w") as f:
            f.write(refresh_token)

def refresh_access_token():
    if not os.path.exists("refresh_token.txt"):
        raise Exception("No refresh token found. Please login again.")

    refresh_token = open("refresh_token.txt").read().strip()
    data = {
        "client_id": API_KEY,
        "client_secret": API_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(REFRESH_URL, headers=headers, data=data, timeout=20)

    if r.status_code != 200:
        raise Exception("Failed to refresh token: " + r.text)

    tokens = r.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    save_token(access_token, refresh_token)
    print("🔄 Access token refreshed")
    return access_token

def headers():
    token = get_token()
    if not token:
        raise Exception("No access token found. Login first.")
    return {
        "Authorization": f"Bearer {token}",
        "accept": "application/json"
    }

def _get(path, params=None):
    url = BASE + path
    r = requests.get(url, headers=headers(), params=params, timeout=20)
    if r.status_code == 401:
        refresh_access_token()
        r = requests.get(url, headers=headers(), params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def _post(path, data):
    url = BASE + path
    r = requests.post(url, headers=headers(), json=data, timeout=20)
    if r.status_code == 401:
        refresh_access_token()
        r = requests.post(url, headers=headers(), json=data, timeout=20)
    r.raise_for_status()
    return r.json()

# ---- Correct API Wrappers ----
def get_profile():   return _get("/user/profile")
def get_funds():     return _get("/user/get-funds-and-margin")
def get_positions(): return _get("/portfolio/short-term-positions")
def get_holdings():  return _get("/portfolio/long-term-holdings")
def get_orders():    return _get("/order/retrieve-all")
def get_trades():    return _get("/order/trades/get-trades-for-day")

def place_order(symbol, qty, side, order_type="MARKET", product="I", exchange="NSE_EQ"):
    data = {
        "transaction_type": side.upper(),
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

# ---- Flask App ----
app = Flask(__name__)
subscribers, stop_flag = [], False

def safe(fn, *args):
    try:
        return {"ok": True, "data": fn(*args)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def publish(event, data):
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for q in list(subscribers): 
        q.put(msg)

def polling_worker():
    while not stop_flag:
        snapshot = {
            "profile": safe(get_profile),
            "funds": safe(get_funds),
            "positions": safe(get_positions),
            "holdings": safe(get_holdings),
            "orders": safe(get_orders),
            "trades": safe(get_trades),
        }
        publish("snapshot", snapshot)
        time.sleep(5)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    url = f"{AUTH_DIALOG}?response_type=code&client_id={API_KEY}&redirect_uri={REDIRECT_URI}&state=123"
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Missing code", 400

    data = {
        "code": code,
        "client_id": API_KEY,
        "client_secret": API_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(TOKEN_URL, headers=headers, data=data, timeout=25)

    if r.status_code != 200:
        return f"❌ Token exchange failed: {r.text}", 400

    tokens = r.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        return f"❌ No access token in response: {r.text}", 500

    save_token(access_token, refresh_token)
    print("✅ Access + Refresh tokens updated")
    return redirect("/")

@app.route("/place_order", methods=["POST"])
def place_order_route():
    body = request.json
    try:
        res = place_order(body["symbol"], int(body["qty"]), body["side"])
        publish("botmsg", {"msg": f"✅ Order placed: {body['side']} {body['qty']} {body['symbol']}"})
        return {"ok": True, "data": res}
    except Exception as e:
        publish("botmsg", {"msg": f"❌ Order failed: {str(e)}"})
        return {"ok": False, "error": str(e)}, 400

@app.route("/stream")
def stream():
    from queue import Queue
    q = Queue(); subscribers.append(q)
    def gen():
        try:
            while True: 
                yield q.get()
        except GeneratorExit: 
            subscribers.remove(q)
    return Response(gen(), mimetype="text/event-stream")

if __name__ == "__main__":
    threading.Thread(target=polling_worker, daemon=True).start()
    app.run(port=8000, debug=True)
