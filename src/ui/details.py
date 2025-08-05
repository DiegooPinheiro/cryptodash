from src.services import persistence
# src/ui/details.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import webbrowser
from io import BytesIO

from src.services import coingecko
from src.config import DEFAULT_FIAT

# tenta usar Pillow para exibir imagem; se não tiver, será opcional
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


class Details(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        title = ttk.Label(self, text="Detalhes da Moeda", font=("Arial", 16, "bold"))
        title.pack(pady=8)

        # topo com nome e imagem
        top = ttk.Frame(self)
        top.pack(fill="x", padx=12)

        self.img_label = ttk.Label(top)
        self.img_label.pack(side="right", padx=8)

        self.name_label = ttk.Label(top, text="", font=("Arial", 14, "bold"))
        self.name_label.pack(side="left", padx=6)

        # area de info rápida (preços)
        info_frame = ttk.Frame(self)
        info_frame.pack(fill="x", padx=12, pady=6)
        self.price_usd = ttk.Label(info_frame, text="USD: --")
        self.price_usd.pack(anchor="w")
        self.price_brl = ttk.Label(info_frame, text="BRL: --")
        self.price_brl.pack(anchor="w")
        self.market_cap = ttk.Label(info_frame, text="Market Cap: --")
        self.market_cap.pack(anchor="w")
        self.last_update = ttk.Label(info_frame, text="Última atualização: --")
        self.last_update.pack(anchor="w")

        # descrição (scroll)
        ttk.Label(self, text="Descrição:").pack(anchor="w", padx=12)
        self.desc_area = scrolledtext.ScrolledText(self, height=10, wrap="word", state="disabled")
        self.desc_area.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # links
        link_frame = ttk.Frame(self)
        link_frame.pack(fill="x", padx=12, pady=6)
        self.homepage_btn = ttk.Button(link_frame, text="Abrir site oficial", command=self.open_homepage, state="disabled")
        self.homepage_btn.pack(side="left")
        self.back_btn = ttk.Button(link_frame, text="Voltar", command=lambda: controller.show_frame("Dashboard"))
        self.back_btn.pack(side="right")

        # status
        self.status_label = ttk.Label(self, text="", foreground="blue")
        self.status_label.pack(pady=6)

        # placeholder para imagem tk
        self._tk_image = None
        # guarda dados da moeda atual
        self.current_data = None

    def on_show(self):
        """
        Chamado pelo App.show_frame antes de exibir o frame.
        Inicia a busca automática dos detalhes se houver uma moeda selecionada.
        """
        coin = getattr(self.controller, "selected_coin", None)
        if not coin:
            # sem moeda selecionada, mostra aviso
            self.clear_fields()
            self.status_label.config(text="Nenhuma moeda selecionada.", foreground="orange")
            return

        # inicia fetch em thread
        self.status_label.config(text="Carregando detalhes...", foreground="blue")
        thread = threading.Thread(target=self.fetch_details, args=(coin,), daemon=True)
        thread.start()

    def fetch_details(self, coin_id):
        try:
            data = coingecko.get_coin_details(coin_id)
            self.after(0, self.populate, data)
            # salvar em DB simples (opcional): persistence.save_price(coin_id, data)  # note: different structure
        except Exception as e:
            # tentativa de fallback: carregar do cache
            cached = persistence.load_price(coin_id)
            if cached and cached.get("data"):
                # cached['data'] pode ser payload simples; não é igual ao /coins/{id} — mas é melhor que nada
                self.after(0, self.populate_from_cache, cached)
            else:
                self.after(0, self.show_error, str(e))


    def populate(self, data):
        """
        Popula a UI com os dados retornados pela API /coins/{id}
        """
        self.current_data = data
        name = data.get("name", "")
        symbol = data.get("symbol", "").upper()
        self.name_label.config(text=f"{name} ({symbol})")

        # preços: tenta extrair market_data
        market = data.get("market_data", {}) or {}
        usd = market.get("current_price", {}).get("usd")
        brl = market.get("current_price", {}).get("brl")
        mc = market.get("market_cap", {}).get("usd")

        self.price_usd.config(text=f"USD: ${usd:,.2f}" if usd else "USD: --")
        self.price_brl.config(text=f"BRL: R${brl:,.2f}" if brl else "BRL: --")
        self.market_cap.config(text=f"Market Cap: ${mc:,.2f}" if mc else "Market Cap: --")

        # última atualização
        last = data.get("last_updated")
        self.last_update.config(text=f"Última atualização: {last}" if last else "Última atualização: --")

        # descrição (pode ser HTML obtido do API): pegar o texto em pt ou en
        descr = ""
        desc_field = data.get("description", {})
        if isinstance(desc_field, dict):
            # prefira 'en', depois a primeira disponível
            descr = desc_field.get("en") or next(iter(desc_field.values()), "")
        else:
            descr = str(desc_field or "")

        # limpa tags HTML simples (opcional). Aqui apenas corta muito longo.
        descr = descr.strip()
        if len(descr) > 4000:
            descr = descr[:4000] + "... (cortado)"

        self.desc_area.config(state="normal")
        self.desc_area.delete("1.0", tk.END)
        self.desc_area.insert(tk.END, descr or "Sem descrição disponível.")
        self.desc_area.config(state="disabled")

        # imagem / logo
        image_info = data.get("image", {}) or {}
        img_url = image_info.get("large") or image_info.get("thumb") or image_info.get("small")
        if img_url and PIL_AVAILABLE:
            # tentar carregar imagem (bloqueante) — pequeno size, está OK
            try:
                import requests
                resp = requests.get(img_url, timeout=10)
                resp.raise_for_status()
                img_data = resp.content
                img = Image.open(BytesIO(img_data))
                img.thumbnail((120, 120))
                self._tk_image = ImageTk.PhotoImage(img)
                self.img_label.config(image=self._tk_image, text="")
            except Exception:
                self.img_label.config(image="", text="(imagem não disponível)")
                self._tk_image = None
        else:
            # sem pillow ou sem url: mostrar texto com link (ou url)
            if img_url:
                self.img_label.config(image="", text="(imagem: disponível)")
                # armazenar url para abrir se quiser
                self._image_url = img_url
            else:
                self.img_label.config(image="", text="(sem imagem)")
                self._image_url = None

        # habilita botão homepage se existir
        links = data.get("links", {}) or {}
        homepage = links.get("homepage", [])
        if homepage and isinstance(homepage, list) and homepage[0]:
            self._homepage = homepage[0]
            self.homepage_btn.config(state="normal")
        else:
            self._homepage = None
            self.homepage_btn.config(state="disabled")

        self.status_label.config(text="Detalhes carregados.", foreground="green")

    def open_homepage(self):
        if getattr(self, "_homepage", None):
            webbrowser.open(self._homepage)
        else:
            messagebox.showinfo("Link", "Nenhum site oficial encontrado.")

    def show_error(self, mensagem):
        self.status_label.config(text=f"Erro ao carregar: {mensagem}", foreground="red")
        messagebox.showerror("Erro", mensagem)

    def clear_fields(self):
        self.name_label.config(text="")
        self.price_usd.config(text="USD: --")
        self.price_brl.config(text="BRL: --")
        self.market_cap.config(text="Market Cap: --")
        self.last_update.config(text="Última atualização: --")
        self.desc_area.config(state="normal")
        self.desc_area.delete("1.0", tk.END)
        self.desc_area.config(state="disabled")
        self.img_label.config(image="", text="")
        self.homepage_btn.config(state="disabled")
        self.status_label.config(text="")
