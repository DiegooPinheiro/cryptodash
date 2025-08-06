# src/services/coingecko.py
"""
Client simples para CoinGecko API (endpoints usados pelo CriptoDash).
"""

from typing import List, Dict, Any
import requests
from requests.exceptions import HTTPError, Timeout, RequestException

from src.config import API_BASE_URL, REQUEST_TIMEOUT


def _handle_request_errors(fn_name: str, exc: Exception) -> Exception:
    """Gera exceção amigável para erro de requisição."""
    if isinstance(exc, HTTPError):
        return Exception(f"{fn_name}: Erro HTTP - {exc}")
    if isinstance(exc, Timeout):
        return Exception(f"{fn_name}: Timeout - a API demorou a responder")
    if isinstance(exc, RequestException):
        return Exception(f"{fn_name}: Erro de requisição - {exc}")
    return Exception(f"{fn_name}: Erro inesperado - {exc}")


def get_prices(coin_ids: List[str], vs_currencies: List[str], include_24hr_change: bool = True) -> Dict[str, Any]:
    """
    Busca preços atuais e (opcional) variação 24h das moedas especificadas.

    Args:
        coin_ids: lista de IDs das moedas (ex: ['bitcoin','ethereum'])
        vs_currencies: lista de fiats (ex: ['usd','brl'])
        include_24hr_change: se inclui variação em 24h (bool)

    Returns:
        dict: dados no formato { coin_id: { 'usd': 123.4, 'brl': 567.8, 'usd_24h_change': 1.23 }, ... }

    Raises:
        Exception em caso de erro (mensagem legível).
    """
    endpoint = f"{API_BASE_URL}/simple/price"
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": ",".join(vs_currencies),
        "include_24hr_change": str(include_24hr_change).lower(),
    }

    try:
        resp = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise _handle_request_errors("get_prices", exc)


def get_coin_details(coin_id: str) -> Dict[str, Any]:
    """
    Busca detalhes da moeda (/coins/{id}) — inclui descrição, links, imagens e market_data.

    Args:
        coin_id: ID da moeda (ex: 'bitcoin')

    Returns:
        dict: JSON retornado pela API.

    Raises:
        Exception em caso de erro.
    """
    endpoint = f"{API_BASE_URL}/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }

    try:
        resp = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise _handle_request_errors("get_coin_details", exc)


def get_price_history(coin_id: str, vs_currency: str = "usd", days: int = 1) -> Dict[str, Any]:
    """
    Obtém histórico de preços do endpoint /coins/{id}/market_chart.

    Args:
        coin_id: ID da moeda (ex: 'bitcoin')
        vs_currency: moeda fiat (ex: 'usd')
        days: quantos dias de histórico (1, 7, 30, 'max' também funciona quando passado como str)

    Returns:
        dict: JSON com chaves como 'prices', 'market_caps', 'total_volumes'.
              Ex: { "prices": [[timestamp_ms, price], ...], ... }

    Observação:
        - 'days' aceita inteiros (1,7,30) ou a string 'max'. Aqui recebemos int; se quiser 'max',
          chame a API diretamente (ou chame com days=36500 como workaround).
    """
    endpoint = f"{API_BASE_URL}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": str(days)}

    try:
        resp = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        raise _handle_request_errors("get_price_history", exc)
