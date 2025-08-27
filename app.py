from flask import Flask, render_template, jsonify
import requests, time, threading, atexit, signal, sys
from datetime import datetime

url = "https://api.binance.com/api/v3/ticker/price"
price_data = {"price": None, "time": None}
time_interval = 1

app = Flask(__name__)

# スレッド管理
_stop = threading.Event()
_started = False
_started_lock = threading.Lock()

def fetch_price():
    while not _stop.is_set():
        try:
            res = requests.get(url, params={"symbol": "BTCUSDT"}, timeout=5)
            data = res.json()
            price_data["price"] = data.get("price")
            price_data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("Fetched price:", price_data["price"], "at", price_data["time"], flush=True)
        except Exception as e:
            print("Error fetching price:", e, flush=True)
        _stop.wait(time_interval)  # time.sleep の代わり（停止フラグ対応）

def start_background_once():
    """プロセス内で一度だけバックグラウンド取得を開始"""
    global _started
    with _started_lock:
        if not _started:
            threading.Thread(target=fetch_price, daemon=True).start()
            _started = True
            print("Background thread started", flush=True)

# ★ 起動時に開始（フックに依存しない）
start_background_once()

# 終了時は止める
@atexit.register
def _shutdown():
    _stop.set()
    print("Stopping background thread...", flush=True)

def _handle_term(*_):
    _stop.set()
    sys.exit(0)

signal.signal(signal.SIGTERM, _handle_term)
signal.signal(signal.SIGINT, _handle_term)

@app.route("/")
def index():
    return render_template("index.html", price=price_data["price"], time=price_data["time"])

@app.route("/price")
def get_price():
    if price_data["price"] is not None:
        return jsonify(price_data)
    return jsonify({"error": "Price data not available"}), 503

if __name__ == "__main__":
    app.run(debug=True)
