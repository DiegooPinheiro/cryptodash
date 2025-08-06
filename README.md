# cryptodash
# CriptoDash (Python + Tkinter)

Aplicação simples em Python que consome a API CoinGecko para exibir preços de criptomoedas,
com interface gráfica (Tkinter), persistência local (SQLite), export/import JSON e controles
de auto-refresh.

## Requisitos
- Python 3.8+
- pip

## Instalação
1. Clone / copie o projeto.
2. Crie um virtualenv (recomendado) e ative.
3. Instale dependências:
```bash
py -m pip install -r requirements.txt

py -m pip install matplotlib mplfinance pandas

### Persistência local
- Um banco SQLite em `data/cryptodash.db` guarda configurações e últimos preços.
- O app também grava um **snapshot JSON** em `data/prices.json` toda vez que obtém preços (útil como cache ou para inspeção).

## Estrutura
cryptodash/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── ui/
│   └── services/
├── data/              # DB será criado aqui
├── requirements.txt
├── README.md
└── LICENSE


