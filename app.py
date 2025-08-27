from flask import Flask, render_template, jsonify
import requests, threading, time, signal, sys, os
from datetime import datetime
from typing import Dict, Optional

# Binance API の URL（シンボルは後でパラメータとして渡す）
BINANCE_URL: str = "https://api.binance.com/api/v3/ticker/price"

# 最新価格と時刻を保持する共有辞書
price_data: Dict[str, Optional[str]] = {"price": None, "time": None}

# ポーリング間隔（秒）
POLL_INTERVAL = 1.0

# バックグラウンドスレッドの停止フラグ
_stop_event = threading.Event()
# スレッド起動の二重起動防止用フラグ／ロック
_started = False
_started_lock = threading.Lock()

app = Flask(__name__)

def _poll_price(symbol: str = "BTCUSDT") -> None:
    """Binance API を定期的にポーリングして price_data を更新する。"""
    while not _stop_event.is_set():
        try:
            res = requests.get(BINANCE_URL, params={"symbol": symbol}, timeout=5)
            res.raise_for_status()
            data = res.json()
            if "price" in data:
                price_data["price"] = str(data["price"])
                price_data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Render のログに出力しておく
                print(f"Fetched price: {price_data['price']} at {price_data['time']}", flush=True)
        except Exception as exc:
            print(f"Error fetching price: {exc}", flush=True)
        # 一定時間待機（停止フラグが立っていれば早めに抜ける）
        _stop_event.wait(POLL_INTERVAL)

def _ensure_background_started() -> None:
    """プロセス内で一度だけポーリングスレッドを起動する。"""
    global _started
    with _started_lock:
        if not _started:
            thread = threading.Thread(target=_poll_price, daemon=True)
            thread.start()
            _started = True
            print("Background polling thread started", flush=True)

def _setup_signal_handlers() -> None:
    """終了シグナル受信時にスレッドを停止するハンドラを登録する。"""
    def handle_exit_signal(signum, frame) -> None:
        _stop_event.set()
        print(f"Received signal {signum}; shutting down polling thread", flush=True)
        # devサーバの場合は exit; gunicorn は自身で終了処理する
        if os.getenv("FLASK_ENV") != "production":
            sys.exit(0)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_exit_signal)

@app.route("/")
def index():
    """メインHTMLを返す。JavaScriptは /price をポーリングして更新する。"""
    _ensure_background_started()
    return render_template("index.html", price=price_data["price"], time=price_data["time"])

@app.route("/price")
def get_price():
    """最新価格をJSONで返す。まだ取得できていなければ 503。"""
    _ensure_background_started()
    if price_data["price"] is not None:
        return jsonify(price_data)
    return jsonify({"error": "Price data not available"}), 503

def create_app() -> Flask:
    """Gunicorn 用のアプリファクトリ。"""
    _setup_signal_handlers()
    _ensure_background_started()
    return app

if __name__ == "__main__":
    # ローカル開発時はこちらが実行される
    _setup_signal_handlers()
    _ensure_background_started()
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
