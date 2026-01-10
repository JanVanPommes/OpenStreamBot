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
from core.profile_manager import ProfileManager
from PIL import Image
import signal

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Erscheinungsbild setzen
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.yaml"
# Nutze nun den internen Webserver statt Datei-Pfad
DASHBOARD_URL = "http://localhost:8000/interface/dashboard.html"
VERSION = "0.2.1"

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
        self.geometry("1280x720")
        self.minsize(1280, 720)

        self.bot_process = None
        self.log_queue = queue.Queue()
        self.profile_manager = ProfileManager()
        
        self.kill_existing_bot()
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Set Window Icon
        try:
            icon_path = resource_path("assets/logo.png")
            icon_img = Image.open(icon_path)
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
            logo_path = resource_path("assets/logo.png")
            logo_img = Image.open(logo_path)
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

        self.sidebar_button_5 = ctk.CTkButton(self.sidebar_frame, text="Profiles", command=self.show_profiles_frame)
        self.sidebar_button_5.grid(row=6, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Bot Offline", text_color="gray")
        self.status_label.grid(row=7, column=0, padx=20, pady=(10, 0))

        self.obs_status_label = ctk.CTkLabel(self.sidebar_frame, text="OBS: Offline", text_color="gray")
        self.obs_status_label.grid(row=8, column=0, padx=20, pady=(0, 20))

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
        self.accounts_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_accounts_frame()
        self.actions_frame = ActionEditorFrame(self) # New Editor Frame
        self.profiles_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_profiles_frame()

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
        
        # Configure Tags for ANSI Colors
        # Access underlying tkinter widget for tags
        try:
            tb = self.log_textbox._textbox
            tb.tag_config("red", foreground="#FF5555")
            tb.tag_config("green", foreground="#50FA7B")
            tb.tag_config("yellow", foreground="#F1FA8C")
            tb.tag_config("cyan", foreground="#8BE9FD")
            tb.tag_config("grey", foreground="#6272A4")
            tb.tag_config("reset", foreground="#F8F8F2") # Default/White
        except:
             pass # Fallback if internal structure changes

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
        
        # Sync Button
        self.btn_yt_sync = ctk.CTkButton(self.yt_frame, text="Sync Shorts", command=self.sync_shorts, fg_color="#F59E0B", hover_color="#D97706")
        self.btn_yt_sync.grid(row=0, column=4, padx=10, pady=10)
        
        # Overlay URL Info
        ctk.CTkLabel(self.yt_frame, text="Overlay URL:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.ent_overlay_url = ctk.CTkEntry(self.yt_frame, width=300)
        self.ent_overlay_url.insert(0, "http://localhost:8000/interface/yt_overlay.html")
        self.ent_overlay_url.configure(state="readonly")
        self.ent_overlay_url.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="ew")
        
        ctk.CTkButton(self.yt_frame, text="Copy", width=60, command=self.copy_overlay_url).grid(row=1, column=4, padx=10, pady=5)


        self.update_account_status()
        
        # Check for updates
        self.check_for_updates()

    def check_for_updates(self):
        def run_check():
            try:
                import urllib.request
                import json
                from packaging import version
                
                url = "https://api.github.com/repos/JanVanPommes/OpenStreamBot/releases/latest"
                req = urllib.request.Request(url, headers={'User-Agent': "OpenStreamBot-Launcher"})
                
                with urllib.request.urlopen(req) as response:
                    data = json.load(response)
                    latest_tag = data.get("tag_name", "").lstrip("v")
                    html_url = data.get("html_url", "")
                    
                    current_v = version.parse(VERSION)
                    latest_v = version.parse(latest_tag)
                    
                    if latest_v > current_v:
                        self.show_update_available(latest_tag, html_url)
                        
            except Exception as e:
                print(f"Update check failed: {e}")

        threading.Thread(target=run_check, daemon=True).start()

    def show_update_available(self, new_version, url):
        # Update UI in main thread
        def ui_update():
            btn = ctk.CTkButton(self.sidebar_frame, text=f"Update Avail: v{new_version}", 
                                fg_color="#F59E0B", hover_color="#D97706",
                                command=lambda: webbrowser.open(url))
            btn.grid(row=9, column=0, padx=20, pady=(10, 20))
            
            # Also notify in dashboard log
            self.log_queue.put(f"\n[System] Update Available: v{new_version} (Current: v{VERSION})\n")
        
        self.after(0, ui_update)

    def update_account_status(self):
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

    def sync_shorts(self):
        try:
             with open(".yt_sync_trigger", "w") as f:
                 f.write("sync")
             messagebox.showinfo("Sync Started", "Shorts sync requested!\nCheck the 'Dashboard' console for progress.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def copy_overlay_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.ent_overlay_url.get())
        messagebox.showinfo("Copied", "Overlay URL copied to clipboard!")

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
                redirect_uri = cfg.get('twitch', {}).get('redirect_uri', 'http://localhost:3000')
                
                # Import here to avoid overhead at start
                import asyncio
                from core.auth import perform_twitch_oauth_flow
                import json
                
                creds = asyncio.run(perform_twitch_oauth_flow(cid, secret, redirect_uri=redirect_uri))
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
        self.profiles_frame.grid_forget()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")

    def show_settings_frame(self):
        self.dashboard_frame.grid_forget()
        self.accounts_frame.grid_forget()
        self.actions_frame.grid_forget()
        self.profiles_frame.grid_forget()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")
        self.load_config_to_ui()

    def show_accounts_frame(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.actions_frame.grid_forget()
        self.profiles_frame.grid_forget()
        self.accounts_frame.grid(row=0, column=1, sticky="nsew")
        self.update_account_status()

    def show_actions_frame(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.accounts_frame.grid_forget()
        self.profiles_frame.grid_forget()
        self.actions_frame.grid(row=0, column=1, sticky="nsew")

    def show_profiles_frame(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.accounts_frame.grid_forget()
        self.actions_frame.grid_forget()
        self.profiles_frame.grid(row=0, column=1, sticky="nsew")
        self.refresh_profile_list()

    def setup_profiles_frame(self):
        self.prof_label = ctk.CTkLabel(self.profiles_frame, text="Profile Manager", font=ctk.CTkFont(size=24, weight="bold"))
        self.prof_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Helper Text
        ctk.CTkLabel(self.profiles_frame, text="Profiles allow you to switch between different bot configurations.").grid(row=1, column=0, padx=20, sticky="w")
        
        # Content Area
        self.prof_content = ctk.CTkFrame(self.profiles_frame)
        self.prof_content.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        
        # List
        self.prof_listbox = ctk.CTkScrollableFrame(self.prof_content, width=300, height=300)
        self.prof_listbox.pack(side="left", fill="y", padx=10, pady=10)
        
        # Controls
        self.prof_controls = ctk.CTkFrame(self.prof_content, fg_color="transparent")
        self.prof_controls.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(self.prof_controls, text="Enter Profile Name:").pack(pady=(0,5))
        self.entry_profile = ctk.CTkEntry(self.prof_controls)
        self.entry_profile.pack(pady=5, fill="x")
        
        self.btn_create_prof = ctk.CTkButton(self.prof_controls, text="Save Current as New Profile", command=self.create_profile)
        self.btn_create_prof.pack(pady=10, fill="x")
        
        self.btn_save_prof = ctk.CTkButton(self.prof_controls, text="overwrite Selected Profile", fg_color="orange", command=self.save_to_selected_profile)
        self.btn_save_prof.pack(pady=10, fill="x")
        
        self.btn_load_prof = ctk.CTkButton(self.prof_controls, text="Load Selected Profile", fg_color="green", command=self.load_selected_profile)
        self.btn_load_prof.pack(pady=10, fill="x")
        
        self.btn_del_prof = ctk.CTkButton(self.prof_controls, text="Delete Selected Profile", fg_color="red", command=self.delete_selected_profile)
        self.btn_del_prof.pack(pady=10, fill="x")
        
        self.selected_profile_btn = None
        self.selected_profile_name = None

    def refresh_profile_list(self):
        for w in self.prof_listbox.winfo_children(): w.destroy()
        
        profiles = self.profile_manager.get_profiles()
        for p in profiles:
            btn = ctk.CTkButton(self.prof_listbox, text=p, command=lambda n=p: self.select_profile(n),
                                fg_color="transparent", border_width=1, text_color=("gray10", "gray90"))
            btn.pack(fill="x", pady=2)
            
    def select_profile(self, name):
        self.selected_profile_name = name
        self.entry_profile.delete(0, "end")
        self.entry_profile.insert(0, name)
        # Visual feedback could be added here (highlight button)

    def create_profile(self):
        name = self.entry_profile.get()
        if not name:
            messagebox.showerror("Error", "Please enter a profile name!")
            return
        if not name.isalnum(): # Simple check
             if not messagebox.askyesno("Warning", "Profile name contains special characters. Continue?"): return
             
        self.profile_manager.save_profile(name)
        messagebox.showinfo("Success", f"Profile '{name}' saved.")
        self.refresh_profile_list()

    def save_to_selected_profile(self):
        if not self.selected_profile_name: return
        if messagebox.askyesno("Confirm", f"Overwrite profile '{self.selected_profile_name}' with current settings?"):
            self.profile_manager.save_profile(self.selected_profile_name)
            messagebox.showinfo("Success", "Profile updated.")

    def load_selected_profile(self):
        if not self.selected_profile_name: return
        if self.bot_process:
            if not messagebox.askyesno("Warning", "Bot is running! It must be stopped to load a profile. Stop Bot now?"):
                return
            self.stop_bot()
            
        try:
            self.profile_manager.load_profile(self.selected_profile_name)
            messagebox.showinfo("Success", f"Profile '{self.selected_profile_name}' loaded.\nYou can now start the bot.")
            # Update UI config view if needed
            self.load_config_to_ui()
            # Also Action Editor might need refresh if it was open, but it reloads from file on init. 
            # We can force refresh it:
            self.actions_frame.load_actions() 
            self.actions_frame.refresh_action_list() # This method exists in my head, let's hope it's in gui_actions.py. Yes it is.
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_selected_profile(self):
        if not self.selected_profile_name: return
        if messagebox.askyesno("Confirm", f"Delete profile '{self.selected_profile_name}'?"):
            import shutil
            path = os.path.join(self.profile_manager.profile_dir, self.selected_profile_name)
            try:
                shutil.rmtree(path)
                self.selected_profile_name = None
                self.refresh_profile_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))
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
        if getattr(sys, 'frozen', False):
             # Frozen (compiled) mode
             base_dir = os.path.dirname(sys.executable)
             
             # Locate Bot Executable (created by PyInstaller onedir)
             # Name was set to "bot_internal" in build.py
             exe_name = "bot_internal.exe" if os.name == 'nt' else "bot_internal"
             bot_exe_path = os.path.join(base_dir, "bot_internal", exe_name)
             
             if not os.path.exists(bot_exe_path):
                 messagebox.showerror("Error", f"Bot Executable not found at:\n{bot_exe_path}")
                 return

             cmd = [bot_exe_path]
        else:
             # Dev mode (script)
             if not os.path.exists("./venv/bin/python") and not os.path.exists("./venv/Scripts/python.exe"):
                  # Try system python or just warn? Assuming venv structure.
                  # Let's be robust
                  python_exe = sys.executable
             else:
                  # Check linux/windows venv
                  if os.name == 'nt':
                       python_exe = "./venv/Scripts/python.exe"
                  else:
                       python_exe = "./venv/bin/python"
             
             if not os.path.exists(python_exe):
                  # Fallback
                  python_exe = sys.executable
                  
             cmd = [python_exe, "-u", "main.py"]
        
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
            try:
                self.bot_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.bot_process.kill()
                
            self.bot_process = None
            self.start_btn.configure(text="Start Bot", fg_color="green", hover_color="darkgreen")
            self.status_label.configure(text="Status: Offline", text_color="red")
            self.yt_connect_btn.configure(state="disabled", text="Connect YouTube Stream", fg_color="#FF0000")
            self.log_queue.put("\n[System] Bot stopped.\n")

    def kill_existing_bot(self):
        """Checks for existing bot process from previous run and kills it."""
        import json
        if os.path.exists(".bot_status"):
            try:
                with open(".bot_status", "r") as f:
                    status = json.load(f)
                pid = status.get("pid")
                if pid:
                    try:
                        os.kill(pid, 0) # Check if running
                        print(f"Found orphan bot process {pid}, killing it...")
                        os.kill(pid, signal.SIGTERM)
                        time.sleep(1)
                        try:
                             os.kill(pid, 0)
                             os.kill(pid, signal.SIGKILL)
                        except: pass
                    except OSError:
                        pass # Not running
            except Exception as e:
                print(f"Error cleaning up: {e}")

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

    def append_ansi_text(self, text):
        import re
        # Regex to split by ANSI codes: \033[XXm
        # Captures the code in group
        parts = re.split(r'(\033\[\d+m)', text)
        
        current_tag = "reset"
        
        # Mapping ANSI codes to tags
        ansi_map = {
            '\033[91m': 'red',
            '\033[92m': 'green',
            '\033[93m': 'yellow',
            '\033[96m': 'cyan',
            '\033[90m': 'grey',
            '\033[0m': 'reset'
        }
        
        for part in parts:
            if part in ansi_map:
                current_tag = ansi_map[part]
            else:
                if part: # Ignore empty strings
                    try:
                        self.log_textbox.insert("end", part, current_tag)
                        # Autoscroll
                        self.log_textbox.see("end")
                    except:
                        # Fallback if tags fail
                        self.log_textbox.insert("end", part)

    def update_logs(self):
        while not self.log_queue.empty():
            line = self.log_queue.get()
            self.append_ansi_text(line)
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
                    
                    # PID Check
                    reported_pid = status.get("pid")
                    is_pid_running = False
                    if reported_pid:
                        try:
                            # signal 0 check if process is alive
                            os.kill(reported_pid, 0)
                            is_pid_running = True
                        except OSError:
                            is_pid_running = False
                    
                    # Update Overall Status
                    t_status = "Offline" if (stale or not is_pid_running) else status.get("twitch", "Offline")
                    y_status = "Offline" if (stale or not is_pid_running) else status.get("youtube", "Offline")
                    is_running = self.bot_process and self.bot_process.poll() is None
                    
                    if is_running or is_pid_running:
                        if (t_status == "Online" or y_status == "Polling") and not stale:
                            self.status_label.configure(text="Status: Bot Online", text_color="green")
                        else:
                            self.status_label.configure(text="Status: Bot Starting...", text_color="orange")
                    else:
                        self.status_label.configure(text="Status: Bot Offline", text_color="red")
                    
                    # Update OBS Status
                    o_status = "Offline" if (stale or not is_pid_running) else status.get("obs", "Offline")
                    if o_status == "Connected" and (is_running or is_pid_running) and not stale:
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
