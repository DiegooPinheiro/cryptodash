# src/ui/details.py
import threading
import webbrowser
import re
from io import BytesIO

import customtkinter as ctk
import tkinter.messagebox as messagebox

from src.services import coingecko, persistence
from src.config import DEFAULT_FIAT

# tenta usar Pillow para exibir imagem; se não tiver, será opcional
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


def _safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def _format_currency(value, currency="$"):
    if value is None:
        return "--"
    try:
        return f"{currency}{value:,.2f}"
    except Exception:
        return f"{currency}{value}"


def _strip_html_tags(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r"<(?:.|\n)*?>", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class Details(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Título
        self.title_label = ctk.CTkLabel(self, text="Detalhes da Moeda", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        # Topo: nome + imagem
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.name_label = ctk.CTkLabel(top_frame, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.name_label.pack(side="left", padx=(0, 10))

        self.img_label = ctk.CTkLabel(top_frame, text="(sem imagem)", width=120, height=120, fg_color="#222222", corner_radius=12)
        self.img_label.pack(side="right")

        # Info rápida (preços, market cap, última atualização)
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=20, pady=(0, 15))

        self.price_usd = ctk.CTkLabel(info_frame, text="USD: --", font=ctk.CTkFont(size=14))
        self.price_usd.grid(row=0, column=0, sticky="w", padx=5, pady=2)

        self.price_brl = ctk.CTkLabel(info_frame, text=f"{DEFAULT_FIAT.upper()}: --", font=ctk.CTkFont(size=14))
        self.price_brl.grid(row=0, column=1, sticky="w", padx=5, pady=2)

        self.market_cap = ctk.CTkLabel(info_frame, text="Market Cap: --", font=ctk.CTkFont(size=14))
        self.market_cap.grid(row=1, column=0, sticky="w", padx=5, pady=2)

        self.last_update = ctk.CTkLabel(info_frame, text="Última atualização: --", font=ctk.CTkFont(size=14))
        self.last_update.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        # Descrição (scroll)
        descr_label = ctk.CTkLabel(self, text="Descrição:", font=ctk.CTkFont(size=16, weight="bold"))
        descr_label.pack(anchor="w", padx=20)

        self.desc_area = ctk.CTkTextbox(self, width=700, height=180, corner_radius=12)
        self.desc_area.pack(padx=20, pady=(0, 20), fill="both", expand=False)
        self.desc_area.configure(state="disabled")

        # Links + botões
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.homepage_btn = ctk.CTkButton(btn_frame, text="Abrir site oficial", command=self.open_homepage, state="disabled")
        self.homepage_btn.pack(side="left")

        self.back_btn = ctk.CTkButton(btn_frame, text="Voltar", command=lambda: controller.show_frame("Dashboard"))
        self.back_btn.pack(side="right")

        # Status
        self.status_label = ctk.CTkLabel(self, text="", text_color="#00aaff", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=(0, 15))

        # Placeholder para imagem
        self._tk_image = None
        self._image_url = None

        # Dados atuais
        self.current_data = None
        self._homepage = None

    # Lifecycle
    def on_show(self):
        coin = getattr(self.controller, "selected_coin", None)
        if not coin:
            self.clear_fields()
            self.status_label.configure(text="Nenhuma moeda selecionada.", text_color="#ffaa00")
            return

        self.status_label.configure(text="Carregando detalhes...", text_color="#00aaff")
        threading.Thread(target=self.fetch_details, args=(coin,), daemon=True).start()

    # Fetch
    def fetch_details(self, coin_id: str):
        try:
            data = coingecko.get_coin_details(coin_id)
            try:
                market = data.get("market_data", {}) or {}
                simple_payload = {
                    "usd": market.get("current_price", {}).get("usd"),
                    "brl": market.get("current_price", {}).get("brl"),
                    "usd_24h_change": market.get("price_change_percentage_24h"),
                }
                persistence.save_price(coin_id, simple_payload)
            except Exception:
                pass

            self.after(0, self.populate, data)
        except Exception as e:
            try:
                cached = persistence.load_price(coin_id)
            except Exception:
                cached = None
            if cached and cached.get("data"):
                self.after(0, self.populate_from_cache, cached)
            else:
                self.after(0, self.show_error, str(e))

    # Populate
    def populate(self, data: dict):
        self.current_data = data
        name = data.get("name", "")
        symbol = data.get("symbol", "").upper()
        self.name_label.configure(text=f"{name} ({symbol})")

        market = data.get("market_data", {}) or {}
        usd = _safe_float(market.get("current_price", {}).get("usd"))
        brl = _safe_float(market.get("current_price", {}).get("brl"))
        mc = _safe_float(market.get("market_cap", {}).get("usd"))

        self.price_usd.configure(text=f"USD: {_format_currency(usd, '$')}" if usd is not None else "USD: --")
        self.price_brl.configure(text=f"{DEFAULT_FIAT.upper()}: {_format_currency(brl, 'R$')}" if brl is not None else f"{DEFAULT_FIAT.upper()}: --")
        self.market_cap.configure(text=f"Market Cap: {_format_currency(mc, '$')}" if mc is not None else "Market Cap: --")

        last = data.get("last_updated")
        self.last_update.configure(text=f"Última atualização: {last}" if last else "Última atualização: --")

        descr = ""
        desc_field = data.get("description", {})
        if isinstance(desc_field, dict):
            descr = desc_field.get("en") or next(iter(desc_field.values()), "")
        else:
            descr = str(desc_field or "")

        descr = _strip_html_tags(descr)
        if len(descr) > 4000:
            descr = descr[:4000] + "... (cortado)"

        self.desc_area.configure(state="normal")
        self.desc_area.delete("0.0", "end")
        self.desc_area.insert("0.0", descr or "Sem descrição disponível.")
        self.desc_area.configure(state="disabled")

        image_info = data.get("image", {}) or {}
        img_url = image_info.get("large") or image_info.get("thumb") or image_info.get("small")
        self._image_url = img_url
        if img_url and PIL_AVAILABLE:
            threading.Thread(target=self._load_image_thread, args=(img_url,), daemon=True).start()
        else:
            self.img_label.configure(image=None, text="(sem imagem)")

        links = data.get("links", {}) or {}
        homepage = links.get("homepage", [])
        if homepage and isinstance(homepage, list) and homepage[0]:
            self._homepage = homepage[0]
            self.homepage_btn.configure(state="normal")
        else:
            self._homepage = None
            self.homepage_btn.configure(state="disabled")

        self.status_label.configure(text="Detalhes carregados.", text_color="#00cc66")

    def populate_from_cache(self, cached: dict):
        data = cached.get("data", {})
        usd = _safe_float(data.get("usd"))
        brl = _safe_float(data.get("brl"))
        self.name_label.configure(text=f"{getattr(self.controller, 'selected_coin', '').capitalize()} (cache)")
        self.price_usd.configure(text=f"USD: {_format_currency(usd, '$')}" if usd is not None else "USD: --")
        self.price_brl.configure(text=f"{DEFAULT_FIAT.upper()}: {_format_currency(brl, 'R$')}" if brl is not None else f"{DEFAULT_FIAT.upper()}: --")
        self.market_cap.configure(text="Market Cap: -- (cache)")
        self.last_update.configure(text=f"Última atualização (cache): {cached.get('timestamp', '--')}")
        self.desc_area.configure(state="normal")
        self.desc_area.delete("0.0", "end")
        self.desc_area.insert("0.0", "Dados carregados do cache local.")
        self.desc_area.configure(state="disabled")
        self.img_label.configure(image=None, text="(imagem não disponível)")
        self.status_label.configure(text="Mostrando dados do cache.", text_color="#ffaa00")

    # Imagem
    def _load_image_thread(self, url: str):
        try:
            import requests
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img_data = resp.content
            img = Image.open(BytesIO(img_data))
            img.thumbnail((120, 120))
            tk_img = ImageTk.PhotoImage(img)

            def _apply():
                self._tk_image = tk_img
                self.img_label.configure(image=self._tk_image, text="")

            self.after(0, _apply)
        except Exception:
            def _fail():
                self.img_label.configure(image=None, text="(imagem não disponível)")
                self._tk_image = None
            self.after(0, _fail)

    # Links
    def open_homepage(self):
        if self._homepage:
            webbrowser.open(self._homepage)
        else:
            messagebox.showinfo("Link", "Nenhum site oficial encontrado.")

    def show_error(self, mensagem):
        self.status_label.configure(text=f"Erro ao carregar: {mensagem}", text_color="#ff3300")
        messagebox.showerror("Erro", mensagem)

    def clear_fields(self):
        self.name_label.configure(text="")
        self.price_usd.configure(text="USD: --")
        self.price_brl.configure(text=f"{DEFAULT_FIAT.upper()}: --")
        self.market_cap.configure(text="Market Cap: --")
        self.last_update.configure(text="Última atualização: --")
        self.desc_area.configure(state="normal")
        self.desc_area.delete("0.0", "end")
        self.desc_area.configure(state="disabled")
        self.img_label.configure(image=None, text="")
        self.homepage_btn.configure(state="disabled")
        self.status_label.configure(text="")
