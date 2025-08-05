import requests
from requests.exceptions import HTTPError, Timeout, RequestException
from src.config import API_BASE_URL, REQUEST_TIMEOUT


def get_prices(coin_ids, vs_currencies, include_24hr_change=True):
    """
    Busca preços atuais e variação 24h das moedas especificadas.

    Args:
        coin_ids (list[str]): lista de IDs das moedas, ex: ['bitcoin', 'ethereum']
        vs_currencies (list[str]): lista de moedas fiat, ex: ['usd', 'brl']
        include_24hr_change (bool): se inclui variação de 24h

    Returns:
        dict: dados no formato {coin_id: {fiat: preço, ... , fiat_24h_change: variação, ...}, ...}

    Raises:
        Exception com mensagem de erro detalhada
    """
    endpoint = f"{API_BASE_URL}/simple/price"
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": ",".join(vs_currencies),
        "include_24hr_change": str(include_24hr_change).lower()
    }

    try:
        response = requests.get(endpoint, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except HTTPError as http_err:
        raise Exception(f"Erro HTTP ao buscar preços: {http_err}")
    except Timeout:
        raise Exception("Timeout: a API demorou a responder")
    except RequestException as err:
        raise Exception(f"Erro ao fazer requisição: {err}")
    except Exception as e:
        raise Exception(f"Erro inesperado: {e}")


def get_coin_details(coin_id):
    """
    Busca detalhes de uma moeda pelo seu ID.

    Args:
        coin_id (str): ID da moeda, ex: 'bitcoin'

    Returns:
        dict: dados detalhados da moeda (descrição, links, imagens)

    Raises:
        Exception com mensagem de erro detalhada
    """
    endpoint = f"{API_BASE_URL}/coins/{coin_id}"

    try:
        response = requests.get(endpoint, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except HTTPError as http_err:
        raise Exception(f"Erro HTTP ao buscar detalhes: {http_err}")
    except Timeout:
        raise Exception("Timeout: a API demorou a responder")
    except RequestException as err:
        raise Exception(f"Erro ao fazer requisição: {err}")
    except Exception as e:
        raise Exception(f"Erro inesperado: {e}")
