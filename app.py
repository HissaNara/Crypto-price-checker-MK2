from flask import Flask, render_template, jsonify
import requests, time, threading
from datetime import datetime

url = "https://api.binance.com/api/v3/ticker/price"
price_data = {"price": None, "time": None}
time_interval = 1

app = Flask(__name__)

def fetch_price():
    while True:
        try:
            res = requests.get(url, params={"symbol": "BTCUSDT"})
            data = res.json()
            price_data["price"] = data["price"]
            price_data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("Fetched price:", data["price"], "at", price_data["time"])
        except Exception as e:
            print("Error fetching price:", e)
        time.sleep(time_interval)

@app.before_serving
def start_fetching():
    thread = threading.Thread(target=fetch_price, daemon=True)
    thread.start()

@app.route("/")
def index():
    return render_template("index.html", price=price_data["price"], time=price_data["time"])

@app.route("/price")
def get_price():
    if price_data["price"] is not None:
        return jsonify(price_data)
    else:
        return jsonify({"error": "Price data not available"}), 503

if __name__ == "__main__":
    app.run(debug=True)
