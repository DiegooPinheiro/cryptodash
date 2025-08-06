# 📊 CriptoDash (Python + Tkinter)

Aplicação em Python que consome a API **CoinGecko** para exibir preços de criptomoedas,
com interface gráfica (Tkinter), persistência local (SQLite), export/import JSON e
gráficos de candles em tempo quase real.

---

## 📋 Requisitos
- **Python 3.8+**
- **pip** (gerenciador de pacotes do Python)
- Opcional: Git (para clonar o repositório)

---

## 🛠️ Instalação

1. **Clone ou baixe** o repositório:
   ```bash
   git clone https://github.com/seu-usuario/cryptodash.git
   cd cryptodash
   ```

2. **(Recomendado)** Crie e ative um ambiente virtual:
   - Windows:
     ```powershell
     python -m venv venv
     venv\Scripts\activate
     ```
   - Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```
   Ou instale manualmente:
   ```bash
   pip install requests pillow matplotlib pandas mplfinance
   ```

> 💡 **Nota:** No Linux, pode ser necessário instalar o Tkinter via:
> ```bash
> sudo apt install python3-tk
> ```

---

## ▶️ Executando a aplicação

Na raiz do projeto, execute:
```bash
python -m src.main
```
ou:
```bash
py -m src.main
```

---

## 📂 Estrutura do projeto

```
cryptodash/
├─ src/
│  ├─ main.py               # Inicializa a aplicação Tkinter e registra as telas
│  ├─ config.py             # Configurações centrais (API base, moedas padrão etc.)
│  ├─ services/
│  │  ├─ coingecko.py       # Comunicação com API CoinGecko
│  │  └─ persistence.py     # Persistência local (SQLite e JSON)
│  ├─ ui/
│  │  ├─ dashboard.py       # Tela principal com lista de moedas e auto-refresh
│  │  ├─ details.py         # Tela de detalhes da moeda selecionada
│  │  └─ graph.py           # Tela de gráficos de candles
│  └─ data/                 # Criada automaticamente para DB e snapshots
│     ├─ cryptodash.db      # Banco SQLite (preços e configs)
│     └─ prices.json        # Snapshot JSON dos preços
├─ requirements.txt         # Dependências do projeto
└─ README.md                # Este arquivo
```

---

## 📜 Explicação dos arquivos

- **`main.py`** — cria a janela principal (`tk.Tk`) e gerencia a troca de telas.
- **`config.py`** — define configurações fixas como URLs, timeouts e lista de moedas padrão.
- **`services/coingecko.py`** — faz requisições à API CoinGecko para buscar preços e detalhes.
- **`services/persistence.py`** — salva dados no SQLite e exporta/importa JSON.
- **`ui/dashboard.py`** — exibe lista de moedas, preços e variação 24h.
- **`ui/details.py`** — mostra informações detalhadas da moeda, imagem e link oficial.
- **`ui/graph.py`** — gera gráficos de candles com histórico da moeda.

---

## 💾 Persistência local

- Um **SQLite** (`data/cryptodash.db`) guarda configurações e últimos preços.
- Um **JSON snapshot** (`data/prices.json`) é gravado a cada atualização, servindo como cache ou export.

---

## 📌 Dicas e resolução de problemas

1. **Preços não aparecem ("--")**
   - Teste no Python:
     ```python
     from src.services import coingecko
     print(coingecko.get_prices(["bitcoin"], ["usd", "brl"]))
     ```
     Se der erro, verifique conexão ou bloqueio da API.

2. **Comando `py` não encontrado**
   - Use `python`:
     ```bash
     python -m pip install -r requirements.txt
     python -m src.main
     ```

3. **Erro `tkinter` no Linux**
   - Instale:
     ```bash
     sudo apt install python3-tk
     ```

4. **Aviso `FutureWarning: 'T' is deprecated`**
   - Já corrigido no código (`'T'` → `'min'`). Atualize o `graph.py` se necessário.

---

## 📦 Arquivo `requirements.txt`

```
requests
pillow
matplotlib
pandas
mplfinance
```

---

## 🛡️ Licença

Licenciado sob a **MIT License** — veja o arquivo `LICENSE` para detalhes.

---

## 👩‍💻 Contribuição

- Use branches para novas funcionalidades.
- Teste localmente antes de abrir Pull Requests.
- Siga padrões PEP8 (`black`, `flake8` recomendados).

---
