import threading
import time
import customtkinter as ctk
from tkinter import messagebox, filedialog
from src.services import coingecko, persistence
from src.config import DEFAULT_COINS, DEFAULT_FIAT, AUTO_REFRESH_INTERVAL

try:
    from src.services.persistence import DEFAULT_JSON_SNAPSHOT
except Exception:
    DEFAULT_JSON_SNAPSHOT = None

# Configura tema global
ctk.set_appearance_mode("dark")  # "dark", "light" ou "system"
ctk.set_default_color_theme("blue")  # azul futurista

class Dashboard(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.auto_refresh = ctk.BooleanVar(value=False)
        self.refresh_interval = ctk.IntVar(value=AUTO_REFRESH_INTERVAL)
        self._after_id = None
        self._fetch_in_progress = False

        # Título grande futurista
        self.title = ctk.CTkLabel(self, text="CriptoDash — Dashboard", font=ctk.CTkFont(size=24, weight="bold"))
        self.title.pack(pady=20)

        # Frame controles
        ctrl_frame = ctk.CTkFrame(self)
        ctrl_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(ctrl_frame, text="Selecionar moeda para detalhes:").pack(side="left", padx=(0, 10))
        self.coin_box = ctk.CTkComboBox(ctrl_frame, values=[c.capitalize() for c in DEFAULT_COINS], width=160)
        self.coin_box.pack(side="left")
        if DEFAULT_COINS:
            self.coin_box.set(DEFAULT_COINS[0].capitalize())

        btn_details = ctk.CTkButton(ctrl_frame, text="Ver Detalhes", width=100, command=self.ir_para_detalhes)
        btn_details.pack(side="left", padx=15)

        self.btn_update = ctk.CTkButton(ctrl_frame, text="Atualizar Preços", width=130, command=self.atualizar_precos)
        self.btn_update.pack(side="left", padx=15)

        btn_graph = ctk.CTkButton(ctrl_frame, text="Ver Gráfico", width=100, command=self.ir_para_grafico)
        btn_graph.pack(side="left", padx=15)

        # Auto-refresh
        auto_frame = ctk.CTkFrame(self)
        auto_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.chk_auto = ctk.CTkCheckBox(auto_frame, text="Auto-refresh", variable=self.auto_refresh, command=self._on_toggle_auto_refresh)
        self.chk_auto.pack(side="left")

        ctk.CTkLabel(auto_frame, text="Intervalo (s):").pack(side="left", padx=(20, 8))

        self.interval_slider = ctk.CTkSlider(auto_frame, from_=5, to=300, variable=self.refresh_interval, width=200)
        self.interval_slider.pack(side="left")

        # Status
        self.status_label = ctk.CTkLabel(self, text="", text_color="#00FFA3")
        self.status_label.pack(pady=6)

        # Resultado (lista)
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.pack(padx=20, pady=8, fill="both", expand=True)

        header = ctk.CTkFrame(self.result_frame)
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(header, text="Moeda", width=120, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header, text="USD", width=120, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header, text="BRL", width=120, anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Variação 24h", width=120, anchor="w").pack(side="left", padx=5)

        self.price_labels = {}
        self._build_labels()

        self.load_cached_prices()

        saved_auto = persistence.load_setting("auto_refresh")
        saved_interval = persistence.load_setting("refresh_interval")
        if saved_auto is not None:
            try:
                self.auto_refresh.set(saved_auto == "1")
            except Exception:
                pass
        if saved_interval is not None:
            try:
                self.refresh_interval.set(int(saved_interval))
            except Exception:
                pass
        if self.auto_refresh.get():
            self._schedule_next_refresh(delay_ms=500)

    def _build_labels(self):
        # limpa linhas antigas
        for child in self.result_frame.winfo_children():
            if child != self.result_frame.winfo_children()[0]:
                child.destroy()

        self.price_labels.clear()
        for coin in DEFAULT_COINS:
            row = ctk.CTkFrame(self.result_frame)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=coin.capitalize(), width=120, anchor="w").pack(side="left", padx=5)
            lbl_usd = ctk.CTkLabel(row, text="--", width=120, anchor="w")
            lbl_usd.pack(side="left", padx=5)
            lbl_brl = ctk.CTkLabel(row, text="--", width=120, anchor="w")
            lbl_brl.pack(side="left", padx=5)
            lbl_change = ctk.CTkLabel(row, text="--", width=120, anchor="w")
            lbl_change.pack(side="left", padx=5)
            self.price_labels[coin] = {"usd": lbl_usd, "brl": lbl_brl, "change": lbl_change}

    def _set_status(self, text: str, color: str = "#00FFA3"):
        self.status_label.configure(text=text, text_color=color)

    def _set_ui_busy(self, busy: bool):
        self._fetch_in_progress = busy
        state = "disabled" if busy else "normal"
        try:
            self.btn_update.configure(state=state)
        except Exception:
            pass

    def atualizar_precos(self):
        if self._fetch_in_progress:
            return
        self._set_ui_busy(True)
        self._set_status("Carregando preços...", "#00FFFF")
        thread = threading.Thread(target=self._fetch_and_apply, daemon=True)
        thread.start()

    def _fetch_and_apply(self):
        try:
            data = coingecko.get_prices(DEFAULT_COINS, DEFAULT_FIAT)
            if DEFAULT_JSON_SNAPSHOT:
                try:
                    persistence.save_json_snapshot(DEFAULT_JSON_SNAPSHOT, data)
                except Exception:
                    pass
            for coin, payload in data.items():
                try:
                    persistence.save_price(coin, payload)
                except Exception:
                    pass
            self.after(0, self._apply_prices, data)
        except Exception as exc:
            self.after(0, self._handle_fetch_error, str(exc))

    def _apply_prices(self, data):
        for coin, labels in self.price_labels.items():
            info = data.get(coin, {})
            usd = info.get("usd")
            brl = info.get("brl")
            change = info.get("usd_24h_change")

            labels["usd"].configure(text=f"${usd:,.2f}" if usd is not None else "--")
            labels["brl"].configure(text=f"R${brl:,.2f}" if brl is not None else "--")
            if change is not None:
                txt = f"{change:+.2f}%"
                color = "#00FF00" if change >= 0 else "#FF3300"
                labels["change"].configure(text=txt, text_color=color)
            else:
                labels["change"].configure(text="--", text_color="#AAAAAA")

        self._set_ui_busy(False)
        self._set_status(f"Atualizado em {time.strftime('%Y-%m-%d %H:%M:%S')}", "#00FFA3")

    def _handle_fetch_error(self, message):
        self._set_ui_busy(False)
        self._set_status(f"Erro: {message}", "#FF3300")

    def _on_toggle_auto_refresh(self):
        on = self.auto_refresh.get()
        try:
            persistence.save_setting("auto_refresh", "1" if on else "0")
            persistence.save_setting("refresh_interval", str(self.refresh_interval.get()))
        except Exception:
            pass

        if on:
            self._schedule_next_refresh(delay_ms=200)
            self._set_status("Auto-refresh ligado", "#00FFFF")
        else:
            self._cancel_scheduled_refresh()
            self._set_status("Auto-refresh desligado", "#FFA500")

    def _schedule_next_refresh(self, delay_ms: int | None = None):
        if delay_ms is None:
            delay_ms = max(1, int(self.refresh_interval.get())) * 1000
        self._cancel_scheduled_refresh()
        self._after_id = self.after(delay_ms, self._auto_refresh_worker)

    def _cancel_scheduled_refresh(self):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            finally:
                self._after_id = None

    def _auto_refresh_worker(self):
        if self._fetch_in_progress:
            self._schedule_next_refresh(delay_ms=1000)
            return
        self.atualizar_precos()
        interval_ms = max(5, int(self.refresh_interval.get())) * 1000
        self._schedule_next_refresh(delay_ms=interval_ms)

    def load_cached_prices(self):
        data = {}
        for coin in DEFAULT_COINS:
            try:
                rec = persistence.load_price(coin)
            except Exception:
                rec = None
            if rec and isinstance(rec.get("data"), dict):
                data[coin] = rec["data"]

        if not data and DEFAULT_JSON_SNAPSHOT:
            try:
                snap = persistence.load_json_snapshot(DEFAULT_JSON_SNAPSHOT)
                if snap and isinstance(snap.get("prices"), dict):
                    data = snap["prices"]
            except Exception:
                data = {}

        if data:
            self._apply_prices(data)

    def ir_para_detalhes(self):
        sel = self.coin_box.get()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione uma moeda antes de ver detalhes.")
            return
        coin_id = sel.lower()
        self.controller.selected_coin = coin_id
        self.controller.show_frame("Details")

    def ir_para_grafico(self):
        self.controller.show_frame("GraphFrame")
