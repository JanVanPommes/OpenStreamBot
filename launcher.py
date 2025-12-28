import customtkinter as ctk
import subprocess
import threading
import sys
import yaml
import os
import signal
import webbrowser
import queue
import time
from tkinter import messagebox
from interface.gui_actions import ActionEditorFrame
from PIL import Image

# Erscheinungsbild setzen
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.yaml"
# Nutze nun den internen Webserver statt Datei-Pfad
DASHBOARD_URL = "http://localhost:8000/interface/dashboard.html"

class ConsoleRedirector:
    def __init__(self, text_widget, queue):
        self.text_widget = text_widget
        self.queue = queue

    def write(self, str):
        self.queue.put(str)

    def flush(self):
        pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("OpenStreamBot Launcher")
        self.geometry("800x600")
        self.minsize(800, 600)

        self.bot_process = None
        self.log_queue = queue.Queue()
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Set Window Icon
        try:
            icon_img = Image.open("assets/logo.png")
            icon_tk = ctk.CTkImage(light_image=icon_img, dark_image=icon_img)._light_image # Use raw PIL image for wm_iconphoto
            # Actually Tkinter PhotoImage or PIL ImageTk is needed for wm_iconphoto
            from PIL import ImageTk
            self.icon_photo = ImageTk.PhotoImage(icon_img)
            self.wm_iconphoto(True, self.icon_photo)
        except Exception as e:
            print(f"Failed to set icon: {e}")

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Logo
        try:
            logo_img = Image.open("assets/logo.png")
            logo_ctk = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(80, 80))
            self.logo_image = ctk.CTkLabel(self.sidebar_frame, image=logo_ctk, text="")
            self.logo_image.grid(row=0, column=0, padx=20, pady=(20, 5))
        except Exception as e:
            print(f"Logo not found: {e}")
        
        # Modern text styling with better font
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="OpenStreamBot", 
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=("#3B82F6", "#60A5FA")  # Modern blue gradient
        )
        self.logo_label.grid(row=1, column=0, padx=20, pady=(0, 10))

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.show_dashboard_frame)
        self.sidebar_button_1.grid(row=2, column=0, padx=20, pady=10)
        
        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Settings", command=self.show_settings_frame)
        self.sidebar_button_2.grid(row=3, column=0, padx=20, pady=10)

        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Accounts", command=self.show_accounts_frame)
        self.sidebar_button_3.grid(row=4, column=0, padx=20, pady=10)

        self.sidebar_button_4 = ctk.CTkButton(self.sidebar_frame, text="Actions Editor", command=self.show_actions_frame)
        self.sidebar_button_4.grid(row=5, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Bot Offline", text_color="gray")
        self.status_label.grid(row=6, column=0, padx=20, pady=(10, 0))

        self.obs_status_label = ctk.CTkLabel(self.sidebar_frame, text="OBS: Offline", text_color="gray")
        self.obs_status_label.grid(row=7, column=0, padx=20, pady=(0, 20))

        # Start status monitoring thread
        self.status_thread = threading.Thread(target=self.status_monitor, daemon=True)
        self.status_thread.start()

        # --- Frames ---
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self.setup_dashboard_frame()
        self.setup_settings_frame()
        self.accounts_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_accounts_frame()
        self.actions_frame = ActionEditorFrame(self) # New Editor Frame

        # Start with Dashboard
        self.show_dashboard_frame()

        # Log Updater
        self.after(100, self.update_logs)

    def setup_dashboard_frame(self):
        # Header
        self.dash_label = ctk.CTkLabel(self.dashboard_frame, text="Control Center", font=ctk.CTkFont(size=24, weight="bold"))
        self.dash_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Buttons Area
        self.btn_frame = ctk.CTkFrame(self.dashboard_frame)
        self.btn_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.start_btn = ctk.CTkButton(self.btn_frame, text="Start Bot", command=self.toggle_bot, fg_color="green", hover_color="darkgreen")
        self.start_btn.grid(row=0, column=0, padx=20, pady=20)

        self.open_web_btn = ctk.CTkButton(self.btn_frame, text="Open Web Dashboard", command=self.open_web_dashboard)
        self.open_web_btn.grid(row=0, column=1, padx=20, pady=20)

        # YouTube Stream Control (NEW)
        self.yt_connect_btn = ctk.CTkButton(self.btn_frame, text="Connect YouTube Stream", command=self.connect_youtube_stream, fg_color="#FF0000", hover_color="#CC0000")
        self.yt_connect_btn.grid(row=0, column=2, padx=20, pady=20)
        self.yt_connect_btn.configure(state="disabled") # Initially disabled until bot starts

        # Console Output
        self.console_label = ctk.CTkLabel(self.dashboard_frame, text="Live Log Output:", anchor="w")
        self.console_label.grid(row=2, column=0, padx=20, pady=(20,5), sticky="w")

        self.log_textbox = ctk.CTkTextbox(self.dashboard_frame, width=600, height=300)
        self.log_textbox.grid(row=3, column=0, padx=20, pady=5, sticky="nsew")
        self.dashboard_frame.grid_rowconfigure(3, weight=1)
        self.dashboard_frame.grid_columnconfigure(0, weight=1)

    def setup_settings_frame(self):
        self.settings_label = ctk.CTkLabel(self.settings_frame, text="Configuration", font=ctk.CTkFont(size=24, weight="bold"))
        self.settings_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        self.config_content = ctk.CTkTextbox(self.settings_frame, width=600, height=400)
        self.config_content.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.settings_frame.grid_rowconfigure(1, weight=1)
        self.settings_frame.grid_columnconfigure(0, weight=1)

        self.load_btn = ctk.CTkButton(self.settings_frame, text="Reload Config File", command=self.load_config_to_ui)
        self.load_btn.grid(row=2, column=0, padx=20, pady=10, sticky="e")
        
        # Save Button
        self.save_btn = ctk.CTkButton(self.settings_frame, text="Save Config", command=self.save_config_from_ui)
        self.save_btn.grid(row=2, column=0, padx=20, pady=10, sticky="w")
        
        self.load_config_to_ui()

    # --- ACCOUNTS FRAME ---
    def setup_accounts_frame(self):
        self.acc_label = ctk.CTkLabel(self.accounts_frame, text="Manage Accounts", font=ctk.CTkFont(size=24, weight="bold"))
        self.acc_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Twitch Section
        self.twitch_frame = ctk.CTkFrame(self.accounts_frame)
        self.twitch_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.twitch_frame, text="Twitch", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.twitch_status = ctk.CTkLabel(self.twitch_frame, text="Checking...", text_color="gray")
        self.twitch_status.grid(row=0, column=1, padx=10)
        
        self.btn_twitch_login = ctk.CTkButton(self.twitch_frame, text="Login with Twitch", command=self.login_twitch)
        self.btn_twitch_login.grid(row=0, column=2, padx=10, pady=10)
        
        self.btn_twitch_logout = ctk.CTkButton(self.twitch_frame, text="Logout", command=self.logout_twitch, fg_color="red", hover_color="darkred")
        self.btn_twitch_logout.grid(row=0, column=3, padx=10, pady=10)

        # YouTube Section
        self.yt_frame = ctk.CTkFrame(self.accounts_frame)
        self.yt_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.yt_frame, text="YouTube", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.yt_status = ctk.CTkLabel(self.yt_frame, text="Checking...", text_color="gray")
        self.yt_status.grid(row=0, column=1, padx=10)
        
        self.btn_yt_login = ctk.CTkButton(self.yt_frame, text="Login with Google", command=self.login_youtube)
        self.btn_yt_login.grid(row=0, column=2, padx=10, pady=10)

        self.btn_yt_logout = ctk.CTkButton(self.yt_frame, text="Logout", command=self.logout_youtube, fg_color="red", hover_color="darkred")
        self.btn_yt_logout.grid(row=0, column=3, padx=10, pady=10)

        self.update_account_status()

    def update_account_status(self):
        # Twitch Check
        if os.path.exists("token_twitch.json"):
            self.twitch_status.configure(text="Connected", text_color="green")
            self.btn_twitch_login.configure(state="disabled")
            self.btn_twitch_logout.configure(state="normal")
        else:
            self.twitch_status.configure(text="Not Connected", text_color="red")
            self.btn_twitch_login.configure(state="normal")
            self.btn_twitch_logout.configure(state="disabled")

        # YouTube Check
        if os.path.exists("token_youtube.json"):
            self.yt_status.configure(text="Connected", text_color="green")
            self.btn_yt_login.configure(state="disabled")
            self.btn_yt_logout.configure(state="normal")
        else:
            self.yt_status.configure(text="Not Connected", text_color="red")
            self.btn_yt_login.configure(state="normal")
            self.btn_yt_logout.configure(state="disabled")

    def login_twitch(self):
        # Async Logic im Launcher Thread ist doof -> Sub Thread der asyncio run macht
        def run_login():
            try:
                # Load Config to get Client ID
                import yaml
                with open(CONFIG_FILE, 'r') as f:
                    cfg = yaml.safe_load(f)
                
                cid = cfg['twitch']['client_id']
                secret = cfg['twitch']['client_secret']
                
                # Import here to avoid overhead at start
                import asyncio
                from core.auth import perform_twitch_oauth_flow
                import json
                
                creds = asyncio.run(perform_twitch_oauth_flow(cid, secret))
                with open("token_twitch.json", "w") as f:
                    json.dump(creds, f)
                    
                self.after(0, self.update_account_status)
                messagebox.showinfo("Success", "Twitch Login successful!")
                
            except Exception as e:
                messagebox.showerror("Login Error", str(e))

        threading.Thread(target=run_login, daemon=True).start()

    def logout_twitch(self):
        if os.path.exists("token_twitch.json"):
            os.remove("token_twitch.json")
            self.update_account_status()

    def login_youtube(self):
        def run_login():
            try:
                from core.auth import perform_youtube_oauth_flow
                
                # Check config for filenames if needed, assume defaults for now
                perform_youtube_oauth_flow("client_secret.json", "token_youtube.json")
                
                self.after(0, self.update_account_status)
                messagebox.showinfo("Success", "YouTube Login successful!")
            except Exception as e:
                messagebox.showerror("Login Error", str(e))

        threading.Thread(target=run_login, daemon=True).start()

    def logout_youtube(self):
        if os.path.exists("token_youtube.json"):
            os.remove("token_youtube.json")
            self.update_account_status()

    def show_dashboard_frame(self):
        self.settings_frame.grid_forget()
        self.accounts_frame.grid_forget()
        self.actions_frame.grid_forget()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")

    def show_settings_frame(self):
        self.dashboard_frame.grid_forget()
        self.accounts_frame.grid_forget()
        self.actions_frame.grid_forget()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")
        self.load_config_to_ui()

    def show_accounts_frame(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.actions_frame.grid_forget()
        self.accounts_frame.grid(row=0, column=1, sticky="nsew")
        self.update_account_status()

    def show_actions_frame(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.accounts_frame.grid_forget()
        self.actions_frame.grid(row=0, column=1, sticky="nsew")

    def load_config_to_ui(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                content = f.read()
                self.config_content.delete("0.0", "end")
                self.config_content.insert("0.0", content)
        except FileNotFoundError:
            self.config_content.insert("0.0", "# Config file not found!\n# Please create config.yaml")

    def save_config_from_ui(self):
        content = self.config_content.get("0.0", "end")
        try:
            # Validate YAML
            yaml.safe_load(content)
            with open(CONFIG_FILE, "w") as f:
                f.write(content)
            messagebox.showinfo("Success", "Configuration saved!")
        except yaml.YAMLError as e:
            messagebox.showerror("Error", f"Invalid YAML format:\n{e}")

    def toggle_bot(self):
        if self.bot_process is None:
            self.start_bot()
        else:
            self.stop_bot()

    def start_bot(self):
        if not os.path.exists("./venv/bin/python"):
             messagebox.showerror("Error", "Virtual environment not found in ./venv")
             return

        cmd = ["./venv/bin/python", "-u", "main.py"] # -u required for unbuffered output
        
        try:
            # Start process properly
            self.bot_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start thread to read output
            self.read_thread = threading.Thread(target=self.read_output, daemon=True)
            self.read_thread.start()

            self.start_btn.configure(text="Stop Bot", fg_color="red", hover_color="darkred")
            self.status_label.configure(text="Status: Starting...", text_color="orange")
            
            # Enable YouTube button if YouTube is configured
            try:
                with open(CONFIG_FILE, 'r') as f:
                    cfg = yaml.safe_load(f)
                if cfg.get('youtube', {}).get('enabled', False):
                    self.yt_connect_btn.configure(state="normal")
            except:
                pass
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start bot: {e}")

    def stop_bot(self):
        if self.bot_process:
            self.bot_process.terminate()
            self.bot_process = None
            self.start_btn.configure(text="Start Bot", fg_color="green", hover_color="darkgreen")
            self.status_label.configure(text="Status: Offline", text_color="red")
            self.yt_connect_btn.configure(state="disabled", text="Connect YouTube Stream", fg_color="#FF0000")
            self.log_queue.put("\n[System] Bot stopped.\n")

    def read_output(self):
        while self.bot_process and self.bot_process.poll() is None:
            line = self.bot_process.stdout.readline()
            if line:
                self.log_queue.put(line)
        
        # Check if process ended unexpectedly
        if self.bot_process: 
             self.log_queue.put("\n[System] Process exited code: " + str(self.bot_process.returncode))
             self.stop_bot_ui_update()

    def stop_bot_ui_update(self):
        # Safe UI update from thread
        self.bot_process = None
        self.start_btn.configure(text="Start Bot", fg_color="green", hover_color="darkgreen")
        self.status_label.configure(text="Status: Offline", text_color="red")

    def update_logs(self):
        while not self.log_queue.empty():
            line = self.log_queue.get()
            self.log_textbox.insert("end", line)
            self.log_textbox.see("end")
        self.after(100, self.update_logs)

    def open_web_dashboard(self):
        # Open URL directly
        webbrowser.open(DASHBOARD_URL)

    def status_monitor(self):
        """Monitors .bot_status file to update UI indicators"""
        import json
        import os
        while True:
            try:
                if os.path.exists(".bot_status"):
                    with open(".bot_status", "r") as f:
                        status = json.load(f)
                    # Check for stale file (last update > 5s)
                    stale = (time.time() - os.path.getmtime(".bot_status")) > 5
                    
                    # Update Overall Status
                    t_status = "Offline" if stale else status.get("twitch", "Offline")
                    y_status = "Offline" if stale else status.get("youtube", "Offline")
                    is_running = self.bot_process and self.bot_process.poll() is None
                    
                    if is_running:
                        if (t_status == "Online" or y_status == "Polling") and not stale:
                            self.status_label.configure(text="Status: Bot Online", text_color="green")
                        else:
                            self.status_label.configure(text="Status: Bot Starting...", text_color="orange")
                    else:
                        self.status_label.configure(text="Status: Bot Offline", text_color="red")
                    
                    # Update OBS Status
                    o_status = "Offline" if stale else status.get("obs", "Offline")
                    if o_status == "Connected" and is_running and not stale:
                        self.obs_status_label.configure(text="OBS: Connected", text_color="green")
                    else:
                        self.obs_status_label.configure(text="OBS: Offline", text_color="red")
                        
                    # Update YouTube Button Color if streaming
                    y_status = status.get("youtube", "Offline")
                    if y_status == "Polling":
                        self.yt_connect_btn.configure(text="Disconnect YouTube Stream", fg_color="orange")
                    else:
                        if self.bot_process and self.bot_process.poll() is None:
                             # Don't overwrite manually set state if possible, but good for sync
                             pass
                else:
                    # File doesn't exist, bot likely offline
                    if not self.bot_process or self.bot_process.poll() is not None:
                        self.status_label.configure(text="Status: Bot Offline", text_color="red")
                        self.obs_status_label.configure(text="OBS: Offline", text_color="red")
            except:
                pass
            time.sleep(1)

    def connect_youtube_stream(self):
        """Toggle YouTube stream connection"""
        if self.yt_connect_btn.cget("text") == "Connect YouTube Stream":
            # Send command to bot to start YouTube polling
            # We'll use a simple file-based flag for now (could be WebSocket later)
            try:
                with open(".yt_control", "w") as f:
                    f.write("start")
                self.yt_connect_btn.configure(text="Disconnect YouTube Stream", fg_color="orange", hover_color="#CC6600")
                self.log_queue.put("[Launcher] YouTube stream search activated.\n")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to connect YouTube: {e}")
        else:
            # Stop YouTube
            try:
                with open(".yt_control", "w") as f:
                    f.write("stop")
                self.yt_connect_btn.configure(text="Connect YouTube Stream", fg_color="#FF0000", hover_color="#CC0000")
                self.log_queue.put("[Launcher] YouTube stream disconnected.\n")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to disconnect YouTube: {e}")

    def on_closing(self):
        self.stop_bot()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
