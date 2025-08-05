# src/main.py
import tkinter as tk
from src.ui.dashboard import Dashboard
from src.ui.details import Details


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CriptoDash")
        self.geometry("900x600")

        # atributo para passar moeda selecionada entre telas
        self.selected_coin = None

        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (Dashboard, Details):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("Dashboard")

    def show_frame(self, name):
        frame = self.frames[name]
        # permite o frame preparar-se antes de ser mostrado (opcional)
        if hasattr(frame, "on_show"):
            try:
                frame.on_show()
            except Exception:
                pass
        frame.tkraise()


if __name__ == "__main__":
    app = App()
    app.mainloop()
