"""
GraphFrame: exibe gráfico tipo corretora (candlesticks) com histórico salvo no DB
e atualização ao vivo por polling. Usa mplfinance + matplotlib içine Tkinter.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.services import persistence, coingecko
from src.config import DEFAULT_COINS

# mapa de timeframes legíveis -> pandas resample rule
TF_MAP = {
    "1m": "1T",
    "5m": "5T",
    "15m": "15T",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D"
}


class GraphFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Estado do live update
        self._live = False
        self._after_id = None

        # defaults
        self.selected_coin = tk.StringVar(value=(DEFAULT_COINS[0] if DEFAULT_COINS else "bitcoin"))
        self.tf_var = tk.StringVar(value="5m")  # candle timeframe (5m default)
        self.poll_interval = tk.IntVar(value=10)  # seconds

        # Top controls
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Label(top, text="Moeda:").pack(side="left")
        coin_box = ttk.Combobox(top, textvariable=self.selected_coin,
                                values=[c.capitalize() for c in DEFAULT_COINS], state="readonly", width=14)
        coin_box.pack(side="left", padx=6)
        coin_box.current(0)

        ttk.Label(top, text="Timeframe:").pack(side="left", padx=(10, 0))
        tf_box = ttk.Combobox(top, textvariable=self.tf_var,
                              values=list(TF_MAP.keys()), state="readonly", width=6)
        tf_box.pack(side="left", padx=6)

        ttk.Label(top, text="Polling (s):").pack(side="left", padx=(10, 0))
        ttk.Spinbox(top, from_=2, to=300, textvariable=self.poll_interval, width=5).pack(side="left", padx=6)

        self.btn_start = ttk.Button(top, text="Start Live", command=self.toggle_live)
        self.btn_start.pack(side="left", padx=8)

        ttk.Button(top, text="Atualizar Agora", command=self.manual_refresh).pack(side="left", padx=6)
        ttk.Button(top, text="Voltar", command=lambda: controller.show_frame("Dashboard")).pack(side="right")

        # Figure / canvas
        self.fig = Figure(figsize=(9, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # status
        self.status = ttk.Label(self, text="", foreground="blue")
        self.status.pack(anchor="w", padx=10)

        # initial draw
        self.draw_chart()

    # ------------------ data helpers ------------------
    def _load_history_df(self, coin_id: str, lookback_hours: int = 24, max_rows: int = 5000) -> pd.DataFrame:
        """
        Pega histórico do DB via persistence.get_price_history e retorna DataFrame
        com índice datetime e coluna 'price' (USD).
        """
        rows = persistence.get_price_history(coin_id, limit=max_rows)
        if not rows:
            return pd.DataFrame()

        # rows: list of {'data': {...}, 'timestamp': 'YYYY-MM-DD HH:MM:SS'}
        records = []
        for r in rows:
            ts = r.get("timestamp")
            try:
                dt = pd.to_datetime(ts)
            except Exception:
                # tentar parse alternativo
                try:
                    dt = pd.to_datetime(r.get("timestamp", ""))
                except Exception:
                    continue
            price = None
            d = r.get("data") or {}
            # valor esperado em payload: {"usd": value, "brl": ...}
            if isinstance(d, dict):
                price = d.get("usd")
            try:
                price = float(price) if price is not None else None
            except Exception:
                price = None
            if price is None:
                continue
            records.append({"dt": dt, "price": price})

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records).drop_duplicates(subset="dt").set_index("dt").sort_index()
        return df

    def _make_ohlc(self, df_price: pd.DataFrame, timeframe: str = "5m") -> pd.DataFrame:
        """
        Recebe df_price com index datetime e coluna 'price'.
        Retorna DataFrame com Open/High/Low/Close indexado por datetime (required by mplfinance).
        """
        if df_price.empty:
            return pd.DataFrame()

        rule = TF_MAP.get(timeframe, "5T")
        # resample and compute OHLC
        ohlc = df_price['price'].resample(rule).ohlc()
        # volumes are not available — usar zeros
        ohlc['volume'] = 0
        # remove NaN rows
        ohlc = ohlc.dropna()
        return ohlc

    # ------------------ plotting ------------------
    def draw_chart(self):
        """Plota o gráfico atual (candlestick)."""
        coin = self.selected_coin.get().lower()
        tf = self.tf_var.get()
        self.status.config(text=f"Carregando histórico para {coin} ({tf})...")
        df_price = self._load_history_df(coin)
        if df_price.empty:
            # tenta uma fetch a partir da API simples (para popular)
            try:
                # pega preço atual e salva no DB
                raw = coingecko.get_prices([coin], ["usd"])
                if raw and coin in raw:
                    persistence.save_price(coin, raw[coin])
                    df_price = self._load_history_df(coin)
            except Exception:
                pass

        if df_price.empty:
            self.ax.clear()
            self.ax.text(0.5, 0.5, "Sem histórico disponível", ha="center", va="center")
            self.canvas.draw_idle()
            self.status.config(text="Sem dados históricos.")
            return

        ohlc = self._make_ohlc(df_price, timeframe=tf)
        if ohlc.empty:
            # fallback: plot line of raw prices
            self.ax.clear()
            df_plot = df_price.copy()
            df_plot = df_plot.last("200")
            self.ax.plot(df_plot.index, df_plot['price'])
            self.ax.set_title(f"{coin.upper()} - Preço (USD) - linha (fallback)")
            self.fig.autofmt_xdate(rotation=30)
            self.canvas.draw_idle()
            self.status.config(text="Dados insuficientes para candles; mostrando linha.")
            return

        # usa mplfinance para desenhar candles no ax
        self.ax.clear()
        mpf.plot(
            ohlc,
            type='candle',
            ax=self.ax,
            volume=False,
            show_nontrading=False,
            style='charles',
            datetime_format='%Y-%m-%d %H:%M'
        )
        self.ax.set_title(f"{coin.upper()} - Candles {tf}")
        self.canvas.draw_idle()
        self.status.config(text=f"Último: {ohlc.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")

    # ------------------ live control ------------------
    def toggle_live(self):
        if self._live:
            self.stop_live()
        else:
            self.start_live()

    def start_live(self):
        self._live = True
        self.btn_start.config(text="Stop Live")
        # schedule immediate update
        self._schedule_next_update(delay_ms=200)

    def stop_live(self):
        self._live = False
        self.btn_start.config(text="Start Live")
        self._cancel_scheduled_update()

    def _schedule_next_update(self, delay_ms: int | None = None):
        if delay_ms is None:
            delay_ms = max(1, int(self.poll_interval.get())) * 1000
        self._cancel_scheduled_update()
        self._after_id = self.after(delay_ms, self._live_worker)

    def _cancel_scheduled_update(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            finally:
                self._after_id = None

    def _live_worker(self):
        """
        Worker chamado pelo after: faz fetch de preço atual (usando coingecko.get_prices),
        salva no DB e redesenha o gráfico.
        """
        coin = self.selected_coin.get().lower()
        try:
            # busca preço atual da API (uma chamada simples)
            data = coingecko.get_prices([coin], ["usd"])
            if data and coin in data:
                # salva tick no DB
                try:
                    persistence.save_price(coin, data[coin])
                except Exception:
                    pass
        except Exception:
            # não interrompe o fluxo, apenas segue para redraw com DB
            pass

        # redesenha o gráfico com os dados atuais do DB
        try:
            self.draw_chart()
        except Exception:
            pass

        # schedule next if still live
        if self._live:
            interval_ms = max(1, int(self.poll_interval.get())) * 1000
            self._schedule_next_update(delay_ms=interval_ms)

    # manual refresh (button)
    def manual_refresh(self):
        # fetch uma vez e desenha (sem alterar estado live)
        coin = self.selected_coin.get().lower()
        try:
            data = coingecko.get_prices([coin], ["usd"])
            if data and coin in data:
                persistence.save_price(coin, data[coin])
        except Exception:
            pass
        self.draw_chart()