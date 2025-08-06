# src/services/persistence.py
import os
import sqlite3
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# Caminho do banco SQLite
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cryptodash.db"))

# Caminho do snapshot JSON
DEFAULT_JSON_SNAPSHOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "prices.json"))


# ---------- Inicialização do banco ----------
def init_db() -> None:
    """Cria o banco de dados e as tabelas (prices, settings) se não existirem."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # tabela prices
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coin TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    # tabela settings key/value
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.commit()
    conn.close()


# ---------- Funções SQLite ----------
def save_price(coin: str, payload: dict) -> None:
    """
    Salva o preço de uma moeda no banco SQLite.
    O timestamp é salvo no formato 'YYYY-MM-DD HH:MM:SS' (com segundos).
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO prices (coin, data, timestamp) VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now'))",
        (coin, json.dumps(payload, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()


def load_price(coin: str) -> Optional[dict]:
    """
    Carrega o último preço de uma moeda no banco SQLite.
    Retorna {'data': dict, 'timestamp': str} ou None se não existir.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT data, timestamp FROM prices WHERE coin = ? ORDER BY timestamp DESC LIMIT 1",
        (coin,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        try:
            return {"data": json.loads(row[0]), "timestamp": row[1]}
        except Exception:
            return {"data": {}, "timestamp": row[1]}
    return None


def get_price_history(coin: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retorna uma lista de registros históricos para a moeda (mais recentes primeiro).
    Cada item: {'data': dict, 'timestamp': str}
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT data, timestamp FROM prices WHERE coin = ? ORDER BY timestamp DESC LIMIT ?",
        (coin, limit),
    )
    rows = cur.fetchall()
    conn.close()
    history = []
    for row in rows:
        try:
            history.append({"data": json.loads(row[0]), "timestamp": row[1]})
        except Exception:
            history.append({"data": {}, "timestamp": row[1]})
    return history


# ---------- Funções de settings (key/value) ----------
def save_setting(key: str, value: str) -> None:
    """
    Salva ou atualiza uma configuração simples no DB.
    Value deve ser string.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def load_setting(key: str) -> Optional[str]:
    """
    Carrega uma configuração. Retorna string ou None se não existir.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def delete_setting(key: str) -> None:
    """Remove uma configuração do DB."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM settings WHERE key = ?", (key,))
    conn.commit()
    conn.close()


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


# ---------- Export / Import JSON (opcionais) ----------
def export_prices_to_json(path: str, coins: List[str]) -> None:
    """
    Exporta os registros existentes no DB para um JSON em `path`.
    Usa a última entrada por moeda (se existir).
    """
    init_db()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    result: Dict[str, Any] = {}
    for coin in coins:
        rec = load_price(coin)
        if rec:
            result[coin] = {"data": rec.get("data", {}), "fetched_at": rec.get("timestamp")}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"exported_at": datetime.utcnow().isoformat(), "prices": result}, fh, ensure_ascii=False, indent=2)


def import_prices_from_json(path: str) -> List[str]:
    """
    Importa o arquivo JSON (formato compatível com export_prices_to_json) e salva no DB.
    Retorna lista das moedas importadas.
    """
    init_db()
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    prices = payload.get("prices", {})
    imported: List[str] = []
    for coin, obj in prices.items():
        data_obj = obj.get("data", {}) if isinstance(obj, dict) else obj
        timestamp = obj.get("fetched_at", datetime.utcnow().isoformat())
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        # salvar com timestamp fornecido (string)
        cur.execute(
            "INSERT INTO prices (coin, data, timestamp) VALUES (?, ?, ?)",
            (coin, json.dumps(data_obj, ensure_ascii=False), timestamp),
        )
        conn.commit()
        conn.close()
        imported.append(coin)
    return imported


# ---------- Inicializa DB ao importar ----------
init_db()
