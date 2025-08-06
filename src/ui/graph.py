# src/ui/graph.py
"""
GraphFrame: exibe gráfico tipo corretora (candlesticks) com histórico salvo no DB
e atualização ao vivo por polling. Usa mplfinance + matplotlib + customtkinter.
"""

import threading
import customtkinter as ctk
import pandas as pd
import mplfinance as mpf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.services import persistence, coingecko
from src.config import DEFAULT_COINS

TF_MAP = {
    "1m": "1T",
    "5m": "5T",
    "15m": "15T",
    "1h": "1H",
    "4h": "4H",
    "1d": "1D"
}


class GraphFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self._live = False
        self._after_id = None

        # Vars
        self.selected_coin = ctk.StringVar(value=(DEFAULT_COINS[0] if DEFAULT_COINS else "bitcoin"))
        self.tf_var = ctk.StringVar(value="5m")
        self.poll_interval = ctk.IntVar(value=10)

        # Top controls
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(top, text="Moeda:").pack(side="left")
        coin_box = ctk.CTkComboBox(top, variable=self.selected_coin,
                                   values=[c.capitalize() for c in DEFAULT_COINS], width=140)
        coin_box.pack(side="left", padx=8)
        coin_box.set(self.selected_coin.get())

        ctk.CTkLabel(top, text="Timeframe:").pack(side="left", padx=(15, 0))
        tf_box = ctk.CTkComboBox(top, variable=self.tf_var, values=list(TF_MAP.keys()), width=80)
        tf_box.pack(side="left", padx=8)
        tf_box.set(self.tf_var.get())

        ctk.CTkLabel(top, text="Polling (s):").pack(side="left", padx=(15, 0))
        poll_spin = ctk.CTkEntry(top, width=50, textvariable=self.poll_interval)
        poll_spin.pack(side="left", padx=8)

        self.btn_start = ctk.CTkButton(top, text="Start Live", command=self.toggle_live, width=100)
        self.btn_start.pack(side="left", padx=15)

        ctk.CTkButton(top, text="Atualizar Agora", command=self.manual_refresh, width=130).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Voltar", command=lambda: controller.show_frame("Dashboard"), width=80).pack(side="right")

        # Matplotlib figure and canvas
        self.fig = Figure(figsize=(9, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Status label
        self.status = ctk.CTkLabel(self, text="", text_color="#00aaff", anchor="w", font=ctk.CTkFont(size=14))
        self.status.pack(fill="x", padx=12, pady=(0, 12))

        self.draw_chart()

    # Data helpers
    def _load_history_df(self, coin_id: str, lookback_hours: int = 24, max_rows: int = 5000) -> pd.DataFrame:
        rows = persistence.get_price_history(coin_id, limit=max_rows)
        if not rows:
            return pd.DataFrame()

        records = []
        for r in rows:
            ts = r.get("timestamp")
            try:
                dt = pd.to_datetime(ts)
            except Exception:
                try:
                    dt = pd.to_datetime(r.get("timestamp", ""))
                except Exception:
                    continue
            price = None
            d = r.get("data") or {}
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
        if df_price.empty:
            return pd.DataFrame()

        rule = TF_MAP.get(timeframe, "5T")
        ohlc = df_price['price'].resample(rule).ohlc()
        ohlc['volume'] = 0
        ohlc = ohlc.dropna()
        return ohlc

    # Plotting
    def draw_chart(self):
        coin = self.selected_coin.get().lower()
        tf = self.tf_var.get()
        self.status.configure(text=f"Carregando histórico para {coin} ({tf})...")
        df_price = self._load_history_df(coin)
        if df_price.empty:
            try:
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
            self.status.configure(text="Sem dados históricos.")
            return

        ohlc = self._make_ohlc(df_price, timeframe=tf)
        if ohlc.empty:
            self.ax.clear()
            df_plot = df_price.copy()
            df_plot = df_plot.last("200")
            self.ax.plot(df_plot.index, df_plot['price'])
            self.ax.set_title(f"{coin.upper()} - Preço (USD) - linha (fallback)")
            self.fig.autofmt_xdate(rotation=30)
            self.canvas.draw_idle()
            self.status.configure(text="Dados insuficientes para candles; mostrando linha.")
            return

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
        self.status.configure(text=f"Último: {ohlc.index[-1].strftime('%Y-%m-%d %H:%M:%S')}")

    # Live control
    def toggle_live(self):
        if self._live:
            self.stop_live()
        else:
            self.start_live()

    def start_live(self):
        self._live = True
        self.btn_start.configure(text="Stop Live")
        self._schedule_next_update(delay_ms=200)

    def stop_live(self):
        self._live = False
        self.btn_start.configure(text="Start Live")
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
        coin = self.selected_coin.get().lower()
        try:
            data = coingecko.get_prices([coin], ["usd"])
            if data and coin in data:
                try:
                    persistence.save_price(coin, data[coin])
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self.draw_chart()
        except Exception:
            pass

        if self._live:
            interval_ms = max(1, int(self.poll_interval.get())) * 1000
            self._schedule_next_update(delay_ms=interval_ms)

    # Manual refresh
    def manual_refresh(self):
        coin = self.selected_coin.get().lower()
        try:
            data = coingecko.get_prices([coin], ["usd"])
            if data and coin in data:
                persistence.save_price(coin, data[coin])
        except Exception:
            pass
        self.draw_chart()
