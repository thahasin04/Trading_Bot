import requests, os

API_KEY = "0f9e7d50-c78c-4421-832f-2ec18358810c"
API_SECRET = "u5of16j49n"
REDIRECT_URI = "http://127.0.0.1:8000/callback"
AUTH_CODE = "NU__dS"   # replace with your latest auth code

TOKEN_URL = "https://api.upstox.com/v2/login/authorization/token"

data = {
    "code": AUTH_CODE,
    "client_id": API_KEY,
    "client_secret": API_SECRET,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
}
headers = {"Content-Type": "application/x-www-form-urlencoded"}

resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=25)

if resp.status_code == 200:
    token = resp.json().get("access_token")
    if token:
        with open("access_token.txt", "w") as f:
            f.write(token)
        print("✅ Access token saved to access_token.txt")
    else:
        print("❌ No access token in response:", resp.json())
else:
    print("❌ Error:", resp.status_code, resp.text)
