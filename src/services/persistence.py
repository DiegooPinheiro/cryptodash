import os
import sqlite3
import json
from typing import Dict, Any, Optional
from datetime import datetime

# Caminho do banco SQLite
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cryptodash.db"))

# Caminho do snapshot JSON
DEFAULT_JSON_SNAPSHOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prices.json"))


# ---------- Inicialização do banco ----------
def init_db():
    """Cria o banco de dados e a tabela de preços, se não existir."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ---------- Funções SQLite ----------
def save_price(coin: str, payload: dict) -> None:
    """Salva o preço de uma moeda no banco SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO prices (coin, data, timestamp) VALUES (?, ?, datetime('now'))",
        (coin, json.dumps(payload))
    )
    conn.commit()
    conn.close()


def load_price(coin: str) -> Optional[dict]:
    """Carrega o último preço de uma moeda no banco SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT data, timestamp FROM prices WHERE coin = ? ORDER BY timestamp DESC LIMIT 1",
        (coin,)
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {"data": json.loads(row[0]), "timestamp": row[1]}
    return None


# ---------- Funções JSON Snapshot ----------
def save_json_snapshot(path: str, data: Dict[str, Any]) -> None:
    """
    Salva um snapshot JSON com:
    {
      "saved_at": "<isoutc>",
      "prices": { "bitcoin": {...}, ... }
    }
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"saved_at": datetime.utcnow().isoformat(), "prices": data}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def load_json_snapshot(path: str) -> Optional[Dict[str, Any]]:
    """Carrega o snapshot JSON salvo."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


# ---------- Executa inicialização do banco ao importar ----------
init_db()
