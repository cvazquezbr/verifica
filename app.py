import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from database import Database
from monitor import MonitorWorker
from wordpress_api import WordPressClient
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import threading

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("WP Plugin Monitor - tagDiv Composer")
        self.geometry("900x600")

        self.db = Database()
        self.monitor_thread = None

        # UI Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="WP Monitor", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard)
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text="Configurações", command=self.show_settings)
        self.btn_settings.grid(row=2, column=0, padx=20, pady=10)

        self.btn_stats = ctk.CTkButton(self.sidebar_frame, text="Estatísticas", command=self.show_stats)
        self.btn_stats.grid(row=3, column=0, padx=20, pady=10)

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.current_frame = None
        self.show_dashboard()

    def clear_main_frame(self):
        if self.current_frame:
            self.current_frame.destroy()

    def show_dashboard(self):
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, sticky="nsew")
        self.current_frame.grid_columnconfigure(0, weight=1)

        site = self.db.get_active_site()
        if not site:
            label = ctk.CTkLabel(self.current_frame, text="Nenhum site configurado.\nVá em Configurações.", font=ctk.CTkFont(size=16))
            label.pack(pady=50)
            return

        site_id, url, user, _, interval = site
        ctk.CTkLabel(self.current_frame, text=f"Monitorando: {url}", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        self.status_label = ctk.CTkLabel(self.current_frame, text="Status: Parado", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=5)

        self.last_check_label = ctk.CTkLabel(self.current_frame, text="Última verificação: -", font=ctk.CTkFont(size=12))
        self.last_check_label.pack(pady=5)

        self.btn_start_stop = ctk.CTkButton(self.current_frame, text="Iniciar Monitoramento",
                                            fg_color="green", command=self.toggle_monitoring)
        self.btn_start_stop.pack(pady=20)

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.btn_start_stop.configure(text="Parar Monitoramento", fg_color="red")
            self.status_label.configure(text="Status: Rodando")

        # Log view
        ctk.CTkLabel(self.current_frame, text="Logs Recentes:").pack(pady=(10, 0))
        self.log_box = ctk.CTkTextbox(self.current_frame, height=200)
        self.log_box.pack(pady=10, padx=20, fill="both", expand=True)

    def toggle_monitoring(self):
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.stop()
            self.btn_start_stop.configure(text="Iniciar Monitoramento", fg_color="green")
            self.status_label.configure(text="Status: Parado")
        else:
            site = self.db.get_active_site()
            if not site:
                messagebox.showerror("Erro", "Configure um site primeiro.")
                return

            self.monitor_thread = MonitorWorker(self.db, site, callback=self.update_status_callback)
            self.monitor_thread.start()
            self.btn_start_stop.configure(text="Parar Monitoramento", fg_color="red")
            self.status_label.configure(text="Status: Rodando")

    def update_status_callback(self, status, was_activated):
        # UI updates must be scheduled on the main thread
        self.after(0, self._update_status_ui, status, was_activated)

    def _update_status_ui(self, status, was_activated):
        now = datetime.now().strftime("%H:%M:%S")

        # Display short status in label
        short_status = status.split('|')[0] if '|' in status else status
        self.status_label.configure(text=f"Status: {short_status}")
        self.last_check_label.configure(text=f"Última verificação: {now}")

        log_msg = f"[{now}] {status}"
        if was_activated:
            log_msg += " (Plugin Reativado!)"

        self.log_box.insert("0.0", log_msg + "\n")

    def show_settings(self):
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.current_frame, text="Configuração do WordPress", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)

        site = self.db.get_active_site()
        current_url = site[1] if site else ""
        current_user = site[2] if site else ""
        current_interval = str(site[4]) if site else "1"

        ctk.CTkLabel(self.current_frame, text="URL do Site:").pack(pady=(10, 0))
        self.ent_url = ctk.CTkEntry(self.current_frame, width=400, placeholder_text="https://exemplo.com")
        self.ent_url.pack(pady=5)
        self.ent_url.insert(0, current_url)

        ctk.CTkLabel(self.current_frame, text="Usuário:").pack(pady=(10, 0))
        self.ent_user = ctk.CTkEntry(self.current_frame, width=400)
        self.ent_user.pack(pady=5)
        self.ent_user.insert(0, current_user)

        ctk.CTkLabel(self.current_frame, text="Application Password:").pack(pady=(10, 0))
        self.ent_pass = ctk.CTkEntry(self.current_frame, width=400, show="*")
        self.ent_pass.pack(pady=5)

        ctk.CTkLabel(self.current_frame, text="Intervalo de Monitoramento (minutos):").pack(pady=(10, 0))
        self.ent_interval = ctk.CTkEntry(self.current_frame, width=400)
        self.ent_interval.pack(pady=5)
        self.ent_interval.insert(0, current_interval)

        self.btn_save = ctk.CTkButton(self.current_frame, text="Salvar e Testar", command=self.save_settings)
        self.btn_save.pack(pady=20)

    def save_settings(self):
        url = self.ent_url.get().strip()
        user = self.ent_user.get().strip()
        pwd = self.ent_pass.get().strip()
        interval = self.ent_interval.get().strip()

        if not url or not user or not pwd or not interval:
            messagebox.showwarning("Aviso", "Preencha todos os campos.")
            return

        try:
            int_interval = int(interval)
            if int_interval < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "Intervalo deve ser um número inteiro maior que 0.")
            return

        # Test connection
        client = WordPressClient(url, user, pwd)
        if client.test_connection():
            self.db.save_site(url, user, pwd, int_interval)
            messagebox.showinfo("Sucesso", "Configurações salvas e conexão testada!")
            self.show_dashboard()
        else:
            messagebox.showerror("Erro", "Não foi possível conectar ao WordPress. Verifique a URL e as credenciais.")

    def show_stats(self):
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame)
        self.current_frame.grid(row=0, column=0, sticky="nsew")

        site = self.db.get_active_site()
        if not site:
            ctk.CTkLabel(self.current_frame, text="Sem dados de estatísticas.").pack(pady=50)
            return

        site_id = site[0]

        tabview = ctk.CTkTabview(self.current_frame)
        tabview.pack(padx=20, pady=20, fill="both", expand=True)

        tab_hourly = tabview.add("Hoje (por Hora)")
        tab_daily = tabview.add("Histórico (por Dia)")

        self.plot_hourly(tab_hourly, site_id)
        self.plot_daily(tab_daily, site_id)

    def on_closing_stats(self):
        # Clean up figures to prevent memory leaks
        plt.close('all')

    def calculate_availability(self, total, activations):
        if total == 0: return 0
        return ((total - activations) / total) * 100

    def plot_hourly(self, master, site_id):
        today = datetime.now().strftime("%Y-%m-%d")
        data = self.db.get_stats_hourly(site_id, today)

        hours = [row[0] for row in data]
        availability = [self.calculate_availability(row[1], row[2]) for row in data]

        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        ax.bar(hours, availability, color='skyblue')
        ax.set_title("Disponibilidade por Hora (Hoje)")
        ax.set_ylabel("% Disponibilidade")
        ax.set_ylim(0, 105)

        canvas = FigureCanvasTkAgg(fig, master=master)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        # Ensure figure is closed when frame is destroyed
        master.bind("<Destroy>", lambda e: plt.close(fig))

    def plot_daily(self, master, site_id):
        data = self.db.get_stats_daily(site_id)

        days = [row[0] for row in data]
        availability = [self.calculate_availability(row[1], row[2]) for row in data]

        # Reverse to show chronological order
        days.reverse()
        availability.reverse()

        fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
        ax.plot(days, availability, marker='o', linestyle='-', color='green')
        ax.set_title("Disponibilidade Diária")
        ax.set_ylabel("% Disponibilidade")
        ax.set_ylim(0, 105)
        plt.xticks(rotation=45)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=master)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        # Ensure figure is closed when frame is destroyed
        master.bind("<Destroy>", lambda e: plt.close(fig))

if __name__ == "__main__":
    app = App()
    app.mainloop()
