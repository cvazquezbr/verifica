import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from database import Database
from monitor import MonitorWorker
from wordpress_api import WordPressClient
from os_utils import set_autostart
import pystray
from PIL import Image
import sys
import os
from email_utils import send_plugin_notification
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import threading

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self, start_minimized=False):
        super().__init__()

        self.title("WP Plugin Monitor - tagDiv Composer")
        self.geometry("900x600")

        self.db = Database()
        self.monitor_thread = None

        # Tray icon setup
        self.tray_icon = None
        self.setup_tray()
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        if start_minimized:
            self.withdraw()

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

        site_id, url, user, _, interval = site[:5]
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
        # Check if we are still in dashboard view and widgets exist
        if not hasattr(self, 'status_label') or not self.status_label.winfo_exists():
            return

        now = datetime.now().strftime("%H:%M:%S")

        # Display short status in label
        short_status = status.split('|')[0] if '|' in status else status
        try:
            self.status_label.configure(text=f"Status: {short_status}")
            self.last_check_label.configure(text=f"Última verificação: {now}")

            log_msg = f"[{now}] {status}"
            if was_activated:
                log_msg += " (Plugin Reativado!)"

            self.log_box.insert("0.0", log_msg + "\n")
        except tk.TclError:
            # Widget might have been destroyed just between check and update
            pass

    def show_settings(self):
        self.clear_main_frame()
        self.current_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.current_frame.grid(row=0, column=0, sticky="nsew")

        tabview = ctk.CTkTabview(self.current_frame)
        tabview.pack(fill="both", expand=True, padx=10, pady=10)

        tab_wp = tabview.add("WordPress")
        tab_email = tabview.add("E-mail (SMTP)")
        tab_system = tabview.add("Sistema")

        site = self.db.get_active_site()

        # --- Tab WordPress ---
        # Using a scrollable frame inside the tab for safety
        wp_container = ctk.CTkScrollableFrame(tab_wp, fg_color="transparent")
        wp_container.pack(fill="both", expand=True)

        ctk.CTkLabel(wp_container, text="Configuração do WordPress", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 20))

        current_url = site[1] if site else ""
        current_user = site[2] if site else ""
        current_interval = str(site[4]) if site else "60"

        ctk.CTkLabel(wp_container, text="URL do Site:").pack(pady=(5, 0))
        self.ent_url = ctk.CTkEntry(wp_container, width=400, placeholder_text="https://exemplo.com")
        self.ent_url.pack(pady=5)
        self.ent_url.insert(0, current_url)

        ctk.CTkLabel(wp_container, text="Usuário WP:").pack(pady=(5, 0))
        self.ent_user = ctk.CTkEntry(wp_container, width=400)
        self.ent_user.pack(pady=5)
        self.ent_user.insert(0, current_user)

        ctk.CTkLabel(wp_container, text="Application Password:").pack(pady=(5, 0))
        self.ent_pass = ctk.CTkEntry(wp_container, width=400, show="*")
        self.ent_pass.pack(pady=5)

        ctk.CTkLabel(wp_container, text="Intervalo de Monitoramento (segundos):").pack(pady=(5, 0))
        self.ent_interval = ctk.CTkEntry(wp_container, width=400)
        self.ent_interval.pack(pady=5)
        self.ent_interval.insert(0, current_interval)

        # --- Tab SMTP ---
        email_container = ctk.CTkScrollableFrame(tab_email, fg_color="transparent")
        email_container.pack(fill="both", expand=True)

        ctk.CTkLabel(email_container, text="Configurações de E-mail (SMTP)", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 20))

        smtp_host = site[5] if site and site[5] else "smtp.gmail.com"
        smtp_port = str(site[6]) if site and site[6] else "465"
        smtp_user = site[7] if site and site[7] else "cvazquezbr@gmail.com"
        smtp_sender_name = site[10] if site and site[10] else "RH - Folha de Ponto"
        smtp_receiver = site[11] if site and site[11] else ""
        smtp_cc = site[12] if site and site[12] else "carlos.vazquez@fattocs.com.br"
        smtp_ssl = site[9] if site is not None and site[9] is not None else 1

        ctk.CTkLabel(email_container, text="Servidor SMTP (Host):").pack(pady=(5, 0))
        self.ent_smtp_host = ctk.CTkEntry(email_container, width=400)
        self.ent_smtp_host.pack(pady=5)
        self.ent_smtp_host.insert(0, smtp_host)

        ctk.CTkLabel(email_container, text="Porta:").pack(pady=(5, 0))
        self.ent_smtp_port = ctk.CTkEntry(email_container, width=400)
        self.ent_smtp_port.pack(pady=5)
        self.ent_smtp_port.insert(0, smtp_port)

        self.var_smtp_ssl = tk.IntVar(value=smtp_ssl)
        self.switch_smtp_ssl = ctk.CTkSwitch(email_container, text="Usar SSL/TLS (Porta 465)", variable=self.var_smtp_ssl)
        self.switch_smtp_ssl.pack(pady=10)

        ctk.CTkLabel(email_container, text="Usuário / E-mail:").pack(pady=(5, 0))
        self.ent_smtp_user = ctk.CTkEntry(email_container, width=400)
        self.ent_smtp_user.pack(pady=5)
        self.ent_smtp_user.insert(0, smtp_user)

        ctk.CTkLabel(email_container, text="Senha:").pack(pady=(5, 0))
        self.ent_smtp_pass = ctk.CTkEntry(email_container, width=400, show="*")
        self.ent_smtp_pass.pack(pady=5)
        if site and site[8]:
             self.ent_smtp_pass.insert(0, site[8])

        ctk.CTkLabel(email_container, text="Nome do Remetente:").pack(pady=(5, 0))
        self.ent_smtp_sender_name = ctk.CTkEntry(email_container, width=400)
        self.ent_smtp_sender_name.pack(pady=5)
        self.ent_smtp_sender_name.insert(0, smtp_sender_name)

        ctk.CTkLabel(email_container, text="E-mail de Destino:").pack(pady=(5, 0))
        self.ent_smtp_receiver = ctk.CTkEntry(email_container, width=400)
        self.ent_smtp_receiver.pack(pady=5)
        self.ent_smtp_receiver.insert(0, smtp_receiver)

        ctk.CTkLabel(email_container, text="E-mail em Cópia (CC):").pack(pady=(5, 0))
        self.ent_smtp_cc = ctk.CTkEntry(email_container, width=400)
        self.ent_smtp_cc.pack(pady=5)
        self.ent_smtp_cc.insert(0, smtp_cc)

        self.btn_test_email = ctk.CTkButton(email_container, text="Testar E-mail", fg_color="orange", text_color="black", command=self.test_email)
        self.btn_test_email.pack(pady=10)

        # --- Tab System ---
        system_container = ctk.CTkScrollableFrame(tab_system, fg_color="transparent")
        system_container.pack(fill="both", expand=True)

        ctk.CTkLabel(system_container, text="Configurações do Sistema", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 20))

        auto_start_mon = site[13] if site and len(site) > 13 else 0
        start_windows = site[14] if site and len(site) > 14 else 0

        self.var_auto_start_mon = tk.IntVar(value=auto_start_mon)
        self.switch_auto_start_mon = ctk.CTkSwitch(system_container, text="Iniciar monitoramento automaticamente ao abrir o App", variable=self.var_auto_start_mon)
        self.switch_auto_start_mon.pack(pady=10, padx=20, anchor="w")

        self.var_start_windows = tk.IntVar(value=start_windows)
        self.switch_start_windows = ctk.CTkSwitch(system_container, text="Iniciar com o Windows (Minimizado)", variable=self.var_start_windows)
        self.switch_start_windows.pack(pady=10, padx=20, anchor="w")

        # Bottom Actions
        self.action_frame = ctk.CTkFrame(self.current_frame, fg_color="transparent")
        self.action_frame.pack(fill="x", pady=10)
        self.btn_save = ctk.CTkButton(self.action_frame, text="Salvar e Testar WordPress", command=self.save_settings)
        self.btn_save.pack(pady=10)

    def get_smtp_config_from_ui(self):
        try:
            port = int(self.ent_smtp_port.get().strip() or 0)
        except ValueError:
            port = 0

        return {
            'host': self.ent_smtp_host.get().strip(),
            'port': port,
            'user': self.ent_smtp_user.get().strip(),
            'pass': self.ent_smtp_pass.get().strip(),
            'ssl': self.var_smtp_ssl.get(),
            'sender_name': self.ent_smtp_sender_name.get().strip(),
            'receiver': self.ent_smtp_receiver.get().strip(),
            'cc': self.ent_smtp_cc.get().strip()
        }

    def test_email(self):
        try:
            smtp_config = self.get_smtp_config_from_ui()
            if not smtp_config['receiver']:
                messagebox.showwarning("Aviso", "Preencha o E-mail de Destino para o teste.")
                return

            plugin_data = {
                'name': 'Teste de Monitoramento',
                'version': '1.0.0',
                'dir': 'teste-monitor',
                'reason': 'E-mail de teste de configuração',
                'wp_admin_url': self.ent_url.get().strip() + "/wp-admin/"
            }

            success = send_plugin_notification(smtp_config, plugin_data)
            if success:
                messagebox.showinfo("Sucesso", "E-mail de teste enviado com sucesso!")
            else:
                messagebox.showerror("Erro", "Falha ao enviar e-mail de teste. Verifique os logs.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao testar e-mail: {e}")

    def save_settings(self):
        url = self.ent_url.get().strip()
        user = self.ent_user.get().strip()
        pwd = self.ent_pass.get().strip()
        interval = self.ent_interval.get().strip()

        if not url or not user or not pwd or not interval:
            messagebox.showwarning("Aviso", "Preencha todos os campos do WordPress.")
            return

        try:
            int_interval = int(interval)
            if int_interval < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Aviso", "Intervalo deve ser um número inteiro maior que 0.")
            return

        smtp_data = self.get_smtp_config_from_ui()
        if not smtp_data['host'] or not smtp_data['user'] or not smtp_data['pass'] or not smtp_data['receiver']:
            messagebox.showwarning("Aviso", "Preencha os campos obrigatórios de SMTP (Host, Usuário, Senha e Destinatário).")
            return

        if smtp_data['port'] <= 0:
            messagebox.showwarning("Aviso", "A porta SMTP deve ser um número válido.")
            return

        auto_start = self.var_auto_start_mon.get()
        start_win = self.var_start_windows.get()

        # Test connection
        client = WordPressClient(url, user, pwd)
        if client.test_connection():
            self.db.save_site(url, user, pwd, int_interval, smtp_data, auto_start, start_win)

            # Apply Windows startup setting
            set_autostart(start_win == 1)

            messagebox.showinfo("Sucesso", "Configurações salvas e conexão WordPress testada!")
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

        # Top Bar with Clear button
        top_bar = ctk.CTkFrame(self.current_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=20, pady=(10, 0))

        btn_clear = ctk.CTkButton(top_bar, text="Limpar Histórico e Otimizar",
                                  fg_color="red", command=self.confirm_clear_logs)
        btn_clear.pack(side="right")

        tabview = ctk.CTkTabview(self.current_frame)
        tabview.pack(padx=20, pady=10, fill="both", expand=True)

        tab_hourly = tabview.add("Hoje (por Hora)")
        tab_daily = tabview.add("Histórico (por Dia)")

        self.plot_hourly(tab_hourly, site_id)
        self.plot_daily(tab_daily, site_id)

    def confirm_clear_logs(self):
        if messagebox.askyesno("Confirmar", "Deseja realmente apagar todo o histórico de estatísticas para economizar espaço?"):
            self.db.clear_logs_and_optimize()
            messagebox.showinfo("Sucesso", "Histórico apagado e banco de dados otimizado!")
            self.show_stats()

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

    def setup_tray(self):
        # Create a simple icon (placeholder or load from file)
        # For now, we'll try to create a simple blue square if no icon file
        try:
            # You might want to use a real icon file here
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                image = Image.new('RGB', (64, 64), color=(0, 120, 215))
        except Exception:
            image = Image.new('RGB', (64, 64), color=(0, 120, 215))

        menu = pystray.Menu(
            pystray.MenuItem('Mostrar', self.show_window, default=True),
            pystray.MenuItem('Sair', self.quit_app)
        )
        self.tray_icon = pystray.Icon("wp_monitor", image, "WP Plugin Monitor", menu)

        # Run tray icon in a separate thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def hide_window(self):
        self.withdraw()

    def show_window(self, icon=None, item=None):
        self.after(0, self.deiconify)
        self.after(0, self.focus_force)

    def quit_app(self, icon=None, item=None):
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.stop()

        if self.tray_icon:
            self.tray_icon.stop()

        self.after(0, self.destroy)
        sys.exit(0)

if __name__ == "__main__":
    start_minimized = "--minimized" in sys.argv
    app = App(start_minimized=start_minimized)

    # Auto-start monitoring if configured
    site = app.db.get_active_site()
    if site and len(site) > 13 and site[13] == 1:
        # Give UI a moment to initialize before starting monitoring
        app.after(1000, app.toggle_monitoring)

    app.mainloop()
