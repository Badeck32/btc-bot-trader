# ✅ server.py PATCH SIGNATURE DEBUG — Version béton armé
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import time
import json
import os

app = Flask(__name__)

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
API_PASSPHRASE = os.getenv("API_PASSPHRASE")
BASE_URL = 'https://api.bitget.com'

def generate_signature(timestamp, method, path, body=''):
    body = body if method.upper() == 'POST' else ''  # FORCE empty string for GET
    content = f"{timestamp}{method.upper()}{path}{body}"
    print("🧪 Signature base string:", content)
    signature = hmac.new(API_SECRET.encode('utf-8'), content.encode('utf-8'), hashlib.sha256).hexdigest()
    print("🔑 Signature générée:", signature)
    return signature

def get_balance():
    timestamp = str(int(time.time() * 1000))
    path = '/api/mix/v1/account/accounts?productType=umcbl'
    sign = generate_signature(timestamp, 'GET', path)
    headers = {
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': API_PASSPHRASE,
        'X-BG-API-KEY': API_KEY  # 🔁 REDONDANT HEADER SÉCURITÉ
    }
    print("📤 Headers GET balance:", headers)
    res = requests.get(BASE_URL + path, headers=headers)
    print("🔎 Résultat balance:", res.text)
    try:
        data = res.json().get('data')
        if not data:
            print("❌ Aucune donnée de balance retournée")
            return 0
        for acc in data:
            if acc.get('marginCoin') == 'USDT':
                return float(acc.get('available', 0))
    except Exception as e:
        print("❌ Erreur parsing balance:", str(e))
    return 0

def place_order(side, symbol, risk_pct=0.03, leverage=20):
    balance = get_balance()
    if balance == 0:
        return {"error": "Balance nulle"}

    max_loss = balance * risk_pct
    entry_price = 1
    sl_distance = 0.01 * entry_price
    qty = round((max_loss * leverage) / sl_distance, 3)

    timestamp = str(int(time.time() * 1000))
    path = '/api/mix/v1/order/placeOrder'
    body = {
        "symbol": symbol,
        "marginCoin": "USDT",
        "size": str(qty),
        "side": side,
        "orderType": "market",
        "force": True,
        "leverage": leverage,
        "openType": "cross"
    }
    body_json = json.dumps(body)
    sign = generate_signature(timestamp, 'POST', path, body_json)
    headers = {
        'ACCESS-KEY': API_KEY,
        'ACCESS-SIGN': sign,
        'ACCESS-TIMESTAMP': timestamp,
        'ACCESS-PASSPHRASE': API_PASSPHRASE,
        'X-BG-API-KEY': API_KEY,
        'Content-Type': 'application/json'
    }
    print("📤 Headers POST:", headers)
    print("📤 Body:", body_json)
    res = requests.post(BASE_URL + path, headers=headers, data=body_json)
    print("✅ Réponse Bitget:", res.text)
    return res.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("📩 Webhook reçu:", data)
        side = data.get("side")
        symbol = data.get("symbol")
        print("🔐 API_KEY (log):", API_KEY)
        print("🔐 PASSPHRASE (log):", API_PASSPHRASE)
        if side and symbol:
            result = place_order(side, symbol)
            return jsonify(result)
        else:
            return {"error": "Missing side or symbol"}, 400
    except Exception as e:
        print("❌ Erreur Webhook:", str(e))
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
