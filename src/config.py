# src/config.py
"""
Configurações do CriptoDash.

Coloque aqui constantes usadas por todo o projeto:
- endpoints da API
- timeouts
- moedas padrão
- caminhos de arquivos
"""

import os

# --- API ---
API_BASE_URL = "https://api.coingecko.com/api/v3"
REQUEST_TIMEOUT = 10  # segundos para requests.get

# --- Moedas padrão ---
# DEFAULT_COINS: lista de coin_ids que aparecem no dashboard por padrão
DEFAULT_COINS = ["bitcoin", "ethereum", "dogecoin", "litecoin", "ripple"]

# DEFAULT_FIAT: fiat padrão utilizado em várias telas (string), ex.: "usd"
DEFAULT_FIAT = "usd"

# DEFAULT_FIATS: lista de fiats (vs_currencies) usada nas chamadas que aceitam múltiplos (ex: simple/price)
DEFAULT_FIATS = ["usd", "brl"]

# --- Auto refresh (em segundos) ---
AUTO_REFRESH_INTERVAL = 10  # segundos padrão de refresh automático

# --- Paths ---
# Caminho absoluto para o banco e logs dentro da pasta data/ do projeto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.abspath(os.path.join(DATA_DIR, "cryptodash.db"))
LOG_FILE = os.path.abspath(os.path.join(PROJECT_ROOT, "app.log"))

# --- Outros ---
# Quantidade máxima de registros a ler para gráficos/histórico (pode ajustar se necessário)
MAX_HISTORY_ROWS = 5000

