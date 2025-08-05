# src/config.py
import os

API_BASE_URL = "https://api.coingecko.com/api/v3"
DEFAULT_COINS = ["bitcoin", "ethereum", "dogecoin", "litecoin", "ripple"]
DEFAULT_FIAT = ["usd", "brl"]
REQUEST_TIMEOUT = 10  # segundos para requests.get
AUTO_REFRESH_INTERVAL = 10  # segundos padrão
DB_FILENAME = os.path.join(os.path.dirname(__file__), "..", "data", "cryptodash.db")
DB_FILENAME = os.path.abspath(DB_FILENAME)
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "app.log")
