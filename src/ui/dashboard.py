from src.services import persistence
from src.services.persistence import DEFAULT_JSON_SNAPSHOT
# src/ui/dashboard.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import os

from src.services import coingecko, persistence
from src.config import DEFAULT_COINS, DEFAULT_FIAT, AUTO_REFRESH_INTERVAL

DEFAULT_INTERVAL = AUTO_REFRESH_INTERVAL


class Dashboard(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Estado
        self.auto_refresh = tk.BooleanVar(value=False)
        self.refresh_interval = tk.IntVar(value=DEFAULT_INTERVAL)
        self._auto_thread = None
        self._stop_auto = threading.Event()

        # Layout
        title = ttk.Label(self, text="CriptoDash — Dashboard", font=("Arial", 18, "bold"))
        title.pack(pady=10)

        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(pady=6, fill="x", padx=12)

        ttk.Label(ctrl_frame, text="Selecionar moeda para detalhes:").pack(side="left", padx=(0, 6))
        self.coin_box = ttk.Combobox(ctrl_frame, values=[c.capitalize() for c in DEFAULT_COINS], state="readonly", width=18)
        self.coin_box.pack(side="left")
        self.coin_box.current(0)

        btn_details = ttk.Button(ctrl_frame, text="Ver Detalhes", command=self.ir_para_detalhes)
        btn_details.pack(side="left", padx=8)

        self.btn_update = ttk.Button(ctrl_frame, text="Atualizar Preços", command=self.atualizar_precos)
        self.btn_update.pack(side="left", padx=8)

        # Auto refresh controls
        auto_frame = ttk.Frame(self)
        auto_frame.pack(fill="x", padx=12, pady=(6, 0))

        self.chk_auto = ttk.Checkbutton(auto_frame, text="Auto-refresh", variable=self.auto_refresh, command=self.toggle_auto_refresh)
        self.chk_auto.pack(side="left")

        ttk.Label(auto_frame, text="Intervalo (s):").pack(side="left", padx=(12, 4))
        self.interval_slider = ttk.Scale(auto_frame, from_=5, to=300, variable=self.refresh_interval, orient="horizontal")
        self.interval_slider.pack(side="left", fill="x", expand=True, padx=6)

        # export/import
       # exp_imp = ttk.Frame(self)
       # exp_imp.pack(fill="x", padx=12, pady=6)
       # ttk.Button(exp_imp, text="Exportar JSON", command=self.export_json).pack(side="left")
       # ttk.Button(exp_imp, text="Importar JSON", command=self.import_json).pack(side="left", padx=6)

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
        self.criar_labels()

        # carregar últimos preços do DB (se houver)
        self.load_cached_prices()

    def criar_labels(self):
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

    def atualizar_precos(self):
        self.btn_update.config(state="disabled")
        self.status_label.config(text="Carregando preços...", foreground="blue")
        thread = threading.Thread(target=self.buscar_precos, daemon=True)
        thread.start()

    def buscar_precos(self):
        try:
            data = coingecko.get_prices(DEFAULT_COINS, DEFAULT_FIAT)
            # salva cada moeda no DB (persistência)
            for coin, payload in data.items():
                persistence.save_price(coin, payload)
            # ---- novo: salvar snapshot JSON em arquivo do projeto ----
            try:
                persistence.save_json_snapshot(DEFAULT_JSON_SNAPSHOT, data)
            except Exception:
                # não interrompe a UI se falhar ao salvar o JSON
                pass
            self.after(0, self.atualizar_labels, data)
        except Exception as e:
            self.after(0, self.mostrar_erro, str(e))


    def atualizar_labels(self, data):
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

        self.status_label.config(text=f"Atualizado em {time.strftime('%H:%M:%S')}", foreground="green")
        self.btn_update.config(state="normal")

    def mostrar_erro(self, mensagem):
        self.status_label.config(text=f"Erro: {mensagem}", foreground="red")
        self.btn_update.config(state="normal")

    # ----------------- Auto-refresh -----------------
    def toggle_auto_refresh(self):
        on = self.auto_refresh.get()
        persistence.save_setting("auto_refresh", "1" if on else "0")
        persistence.save_setting("refresh_interval", str(self.refresh_interval.get()))
        if on:
            self.start_auto_thread()
        else:
            self.stop_auto_thread()

    def start_auto_thread(self):
        if self._auto_thread and self._auto_thread.is_alive():
            return
        self._stop_auto.clear()
        self._auto_thread = threading.Thread(target=self._auto_worker, daemon=True)
        self._auto_thread.start()
        self.status_label.config(text="Auto-refresh ligado", foreground="blue")

    def stop_auto_thread(self):
        self._stop_auto.set()
        self.status_label.config(text="Auto-refresh desligado", foreground="orange")

    def _auto_worker(self):
        # loop até stop flag; respeita o intervalo atual
        while not self._stop_auto.is_set():
            try:
                self.buscar_precos()
            except Exception:
                pass
            interval = int(self.refresh_interval.get()) or DEFAULT_INTERVAL
            # dormir em pequenos passos para poder interromper mais rápido
            for _ in range(interval):
                if self._stop_auto.is_set():
                    break
                time.sleep(1)

    # ----------------- Export / Import -----------------
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

    # ----------------- cached load -----------------
    def load_cached_prices(self):
        """
        Carrega do DB os preços salvos e atualiza os labels (útil no startup).
        Se não houver dados no DB, tenta o snapshot JSON do projeto.
        """
        data = {}
        for coin in DEFAULT_COINS:
            rec = persistence.load_price(coin)
            if rec and isinstance(rec.get("data"), dict):
                data[coin] = rec["data"]

        # se nada no DB, tenta o snapshot JSON
        if not data:
            snap = persistence.load_json_snapshot(DEFAULT_JSON_SNAPSHOT)
            if snap and isinstance(snap.get("prices"), dict):
                data = snap["prices"]

        if data:
            self.atualizar_labels(data)


    # ----------------- Navegação -----------------
    def ir_para_detalhes(self):
        sel = self.coin_box.get()
        if not sel:
            messagebox.showwarning("Seleção", "Selecione uma moeda antes de ver detalhes.")
            return
        coin_id = sel.lower()
        self.controller.selected_coin = coin_id
        self.controller.show_frame("Details")
