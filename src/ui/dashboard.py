# src/ui/dashboard.py
"""
Dashboard do CriptoDash com auto-refresh implementado usando after().
"""

import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.services import coingecko, persistence
from src.config import DEFAULT_COINS, DEFAULT_FIAT, AUTO_REFRESH_INTERVAL

# tenta importar o caminho do snapshot JSON (opcional)
try:
    from src.services.persistence import DEFAULT_JSON_SNAPSHOT  # type: ignore
except Exception:
    DEFAULT_JSON_SNAPSHOT = None


class Dashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Estado
        self.auto_refresh = tk.BooleanVar(value=False)
        self.refresh_interval = tk.IntVar(value=AUTO_REFRESH_INTERVAL)
        self._after_id = None  # id retornado por after() para cancelar agendamento
        self._fetch_in_progress = False  # evita fetchs concorrentes

        # Layout
        title = ttk.Label(self, text="CriptoDash — Dashboard", font=("Arial", 18, "bold"))
        title.pack(pady=10)

        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(pady=6, fill="x", padx=12)

        ttk.Label(ctrl_frame, text="Selecionar moeda para detalhes:").pack(side="left", padx=(0, 6))
        self.coin_box = ttk.Combobox(
            ctrl_frame,
            values=[c.capitalize() for c in DEFAULT_COINS],
            state="readonly",
            width=18,
        )
        self.coin_box.pack(side="left")
        if DEFAULT_COINS:
            self.coin_box.current(0)

        btn_details = ttk.Button(ctrl_frame, text="Ver Detalhes", command=self.ir_para_detalhes)
        btn_details.pack(side="left", padx=8)

        self.btn_update = ttk.Button(ctrl_frame, text="Atualizar Preços", command=self.atualizar_precos)
        self.btn_update.pack(side="left", padx=8)

        # Auto refresh controls
        auto_frame = ttk.Frame(self)
        auto_frame.pack(fill="x", padx=12, pady=(6, 0))

        self.chk_auto = ttk.Checkbutton(
            auto_frame,
            text="Auto-refresh",
            variable=self.auto_refresh,
            command=self._on_toggle_auto_refresh,
        )
        self.chk_auto.pack(side="left")

        ttk.Label(auto_frame, text="Intervalo (s):").pack(side="left", padx=(12, 4))
        self.interval_slider = ttk.Scale(
            auto_frame, from_=5, to=300, variable=self.refresh_interval, orient="horizontal"
        )
        self.interval_slider.pack(side="left", fill="x", expand=True, padx=6)

        # status / loading
        self.status_label = ttk.Label(self, text="", foreground="blue")
        self.status_label.pack(pady=6)

        # resultado
        self.result_frame = ttk.Frame(self)
        self.result_frame.pack(padx=12, pady=8, fill="both", expand=True)
        header = ttk.Frame(self.result_frame)
        header.pack(fill="x", pady=(0, 4))
        ttk.Label(header, text="Moeda", width=20).pack(side="left")
        ttk.Label(header, text="USD", width=18).pack(side="left")
        ttk.Label(header, text="BRL", width=18).pack(side="left")
        ttk.Label(header, text="Variação 24h", width=14).pack(side="left")

        self.price_labels = {}
        self._build_labels()

        # Carrega cache (DB ou JSON)
        self.load_cached_prices()

        # Carrega configurações salvas (se houver) e inicia auto se estava ligado
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
            # agenda a primeira execução breve para começar o ciclo
            self._schedule_next_refresh(delay_ms=500)

    # ---------- UI helpers ----------
    def _build_labels(self):
        # remove linhas exceto header (primeiro filho)
        children = self.result_frame.winfo_children()
        for w in children[1:]:
            w.destroy()

        self.price_labels.clear()
        for coin in DEFAULT_COINS:
            row = ttk.Frame(self.result_frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=coin.capitalize(), width=20).pack(side="left")
            lbl_usd = ttk.Label(row, text="--", width=18)
            lbl_usd.pack(side="left")
            lbl_brl = ttk.Label(row, text="--", width=18)
            lbl_brl.pack(side="left")
            lbl_change = ttk.Label(row, text="--", width=14)
            lbl_change.pack(side="left")
            self.price_labels[coin] = {"usd": lbl_usd, "brl": lbl_brl, "change": lbl_change}

    def _set_status(self, text: str, color: str = "black"):
        self.status_label.config(text=text, foreground=color)

    def _set_ui_busy(self, busy: bool):
        self._fetch_in_progress = busy
        state = "disabled" if busy else "normal"
        try:
            self.btn_update.config(state=state)
        except Exception:
            pass

    # ---------- Fetch / atualização ----------
    def atualizar_precos(self):
        """Inicia fetch em thread (chamado pelo botão)."""
        if self._fetch_in_progress:
            return
        self._set_ui_busy(True)
        self._set_status("Carregando preços...", "blue")
        thread = threading.Thread(target=self._fetch_and_apply, daemon=True)
        thread.start()

    def _fetch_and_apply(self):
        """Chamada em thread: busca na API e aplica resultados via after()."""
        try:
            data = coingecko.get_prices(DEFAULT_COINS, DEFAULT_FIAT)
            # salva snapshot JSON
            if DEFAULT_JSON_SNAPSHOT:
                try:
                    persistence.save_json_snapshot(DEFAULT_JSON_SNAPSHOT, data)
                except Exception:
                    pass
            # salva no DB
            for coin, payload in data.items():
                try:
                    persistence.save_price(coin, payload)
                except Exception:
                    pass
            # aplica na UI
            self.after(0, self._apply_prices, data)
        except Exception as exc:
            self.after(0, self._handle_fetch_error, str(exc))

    def _apply_prices(self, data):
        for coin, labels in self.price_labels.items():
            info = data.get(coin, {})
            usd = info.get("usd")
            brl = info.get("brl")
            change = info.get("usd_24h_change")

            labels["usd"].config(text=f"${usd:,.2f}" if usd is not None else "--")
            labels["brl"].config(text=f"R${brl:,.2f}" if brl is not None else "--")
            if change is not None:
                txt = f"{change:+.2f}%"
                color = "green" if change >= 0 else "red"
                labels["change"].config(text=txt, foreground=color)
            else:
                labels["change"].config(text="--", foreground="black")

        self._set_ui_busy(False)
        # mostra data/hora com segundos
        self._set_status(f"Atualizado em {time.strftime('%Y-%m-%d %H:%M:%S')}", "green")

    def _handle_fetch_error(self, message):
        self._set_ui_busy(False)
        self._set_status(f"Erro: {message}", "red")

    # ---------- Auto-refresh usando after ----------
    def _on_toggle_auto_refresh(self):
        on = self.auto_refresh.get()
        try:
            persistence.save_setting("auto_refresh", "1" if on else "0")
            persistence.save_setting("refresh_interval", str(self.refresh_interval.get()))
        except Exception:
            pass

        if on:
            # inicia ciclo: agenda próxima execução (curto delay para iniciar)
            self._schedule_next_refresh(delay_ms=200)
            self._set_status("Auto-refresh ligado", "blue")
        else:
            self._cancel_scheduled_refresh()
            self._set_status("Auto-refresh desligado", "orange")

    def _schedule_next_refresh(self, delay_ms: int | None = None):
        """Agendar next refresh; cancela agendamento anterior se houver."""
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
        """Executa uma atualização e agenda a próxima (é chamado pelo after)."""
        # evita iniciar se já houver fetch em andamento
        if self._fetch_in_progress:
            # re-agenda após pequeno atraso
            self._schedule_next_refresh(delay_ms=1000)
            return

        # chama atualização (vai rodar em thread)
        self.atualizar_precos()
        # agenda a próxima com base no intervalo atual
        interval_ms = max(5, int(self.refresh_interval.get())) * 1000
        self._schedule_next_refresh(delay_ms=interval_ms)

    # ---------- Cache load ----------
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
            # aplica sem mudar status de carregamento
            self._apply_prices(data)

    # ---------- Export / Import (mantidos por compatibilidade) ----------
    def export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Exportar preços para JSON",
        )
        if not path:
            return
        try:
            persistence.export_prices_to_json(path, DEFAULT_COINS)
            messagebox.showinfo("Exportado", f"Dados exportados para:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro exportar", str(e))

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json"), ("All files", "*.*")], title="Importar preços JSON")
        if not path:
            return
        try:
            imported = persistence.import_prices_from_json(path)
            messagebox.showinfo("Importado", f"Moedas importadas: {', '.join(imported)}")
            self.load_cached_prices()
        except Exception as e:
            messagebox.showerror("Erro importar", str(e))

    # ---------- Navegação ----------
    def ir_para_detalhes(self):
        sel = self.coin_box.get()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione uma moeda antes de ver detalhes.")
            return
        coin_id = sel.lower()
        self.controller.selected_coin = coin_id
        self.controller.show_frame("Details")
