import customtkinter as ctk
import subprocess
import threading
import sys
import yaml
import os
import json
import signal
import webbrowser
import queue
import time
from tkinter import messagebox, filedialog
from interface.gui_actions import ActionEditorFrame
from interface.gui_rewards import RewardEditorFrame
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

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

QUEUE_STATUS_FILE = os.path.join(BASE_DIR, ".queue_status.json")

# Erscheinungsbild setzen
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.yaml"
# Nutze nun den internen Webserver statt Datei-Pfad
DASHBOARD_URL = "http://localhost:8000/interface/dashboard.html"
VERSION = "0.6.0"

def bind_universal_scroll(scrollable_frame):
    """Recursively binds mouse wheel scroll events to a CTkScrollableFrame,
    its canvas, its inner frame, and all current child widgets."""
    if not scrollable_frame:
        return

    canvas = getattr(scrollable_frame, '_parent_canvas', None)
    if not canvas:
        return

    def _on_mouse_wheel(event):
        units = 0
        if hasattr(event, 'num') and event.num == 4:
            units = -1
        elif hasattr(event, 'num') and event.num == 5:
            units = 1
        elif hasattr(event, 'delta') and event.delta:
            units = int(-1 * (event.delta / 120))
            if units == 0:
                units = -1 if event.delta > 0 else 1

        if units != 0:
            try:
                canvas.yview_scroll(units, "units")
            except Exception:
                pass

    def _bind_recursive(w):
        try:
            w.bind("<MouseWheel>", _on_mouse_wheel, add="+")
            w.bind("<Button-4>", _on_mouse_wheel, add="+")
            w.bind("<Button-5>", _on_mouse_wheel, add="+")
        except Exception:
            pass
        try:
            for child in w.winfo_children():
                _bind_recursive(child)
        except Exception:
            pass

    _bind_recursive(scrollable_frame)
    if canvas:
        _bind_recursive(canvas)
    parent_frame = getattr(scrollable_frame, '_parent_frame', None)
    if parent_frame:
        _bind_recursive(parent_frame)

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
        self.minsize(900, 600)

        self.bot_process = None
        self.log_queue = queue.Queue()
        self.profile_manager = ProfileManager()
        
        self.kill_existing_bot()
        self._create_linux_desktop_entry()
        
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
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0, fg_color=("gray80", "#2A2A2A"))
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

        self.logo_label.grid(row=1, column=0, padx=20, pady=(0, 10))

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Control Center", height=40, font=ctk.CTkFont(weight="bold"), fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), text_color=("gray10", "gray90"), hover_color=("gray70", "#4D4D4D"), command=self.show_dashboard_frame)
        self.sidebar_button_1.grid(row=2, column=0, padx=15, pady=8, sticky="ew")
        
        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Configuration", height=40, font=ctk.CTkFont(weight="bold"), fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), text_color=("gray10", "gray90"), hover_color=("gray70", "#4D4D4D"), command=self.show_settings_frame)
        self.sidebar_button_2.grid(row=3, column=0, padx=15, pady=8, sticky="ew")

        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Accounts", height=40, font=ctk.CTkFont(weight="bold"), fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), text_color=("gray10", "gray90"), hover_color=("gray70", "#4D4D4D"), command=self.show_accounts_frame)
        self.sidebar_button_3.grid(row=4, column=0, padx=15, pady=8, sticky="ew")

        self.sidebar_button_rewards = ctk.CTkButton(self.sidebar_frame, text="Twitch Rewards", height=40, font=ctk.CTkFont(weight="bold"), fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), text_color=("gray10", "gray90"), hover_color=("gray70", "#4D4D4D"), command=self.show_rewards_frame)
        self.sidebar_button_rewards.grid(row=5, column=0, padx=15, pady=8, sticky="ew")

        self.sidebar_button_4 = ctk.CTkButton(self.sidebar_frame, text="Actions Editor", height=40, font=ctk.CTkFont(weight="bold"), fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), text_color=("gray10", "gray90"), hover_color=("gray70", "#4D4D4D"), command=self.show_actions_frame)
        self.sidebar_button_4.grid(row=6, column=0, padx=15, pady=8, sticky="ew")

        self.sidebar_button_5 = ctk.CTkButton(self.sidebar_frame, text="Profiles", height=40, font=ctk.CTkFont(weight="bold"), fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), text_color=("gray10", "gray90"), hover_color=("gray70", "#4D4D4D"), command=self.show_profiles_frame)
        self.sidebar_button_5.grid(row=7, column=0, padx=15, pady=8, sticky="ew")

        self.sidebar_button_elevenlabs = ctk.CTkButton(self.sidebar_frame, text="Elevenlabs", height=40, font=ctk.CTkFont(weight="bold"), fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), text_color=("gray10", "gray90"), hover_color=("gray70", "#4D4D4D"), command=self.show_elevenlabs_frame)
        self.sidebar_button_elevenlabs.grid(row=8, column=0, padx=15, pady=8, sticky="ew")

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Bot Offline", text_color="gray")
        self.status_label.grid(row=9, column=0, padx=20, pady=(10, 0))

        self.obs_status_label = ctk.CTkLabel(self.sidebar_frame, text="OBS: Offline", text_color="gray")
        self.obs_status_label.grid(row=10, column=0, padx=20, pady=(0, 10))

        # Version Label
        self.version_label = ctk.CTkLabel(self.sidebar_frame, text=f"v{VERSION}", text_color="gray40", font=ctk.CTkFont(size=10))
        self.version_label.grid(row=11, column=0, padx=20, pady=(0, 10), sticky="s")

        # Start status monitoring thread
        self.status_thread = threading.Thread(target=self.status_monitor, daemon=True)
        self.status_thread.start()

        # Start periodic queue overview update loop
        self.update_queue_overview_loop()

        # --- Frames ---
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self.setup_dashboard_frame()
        self.setup_settings_frame()
        self.accounts_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_accounts_frame()
        self.setup_accounts_frame()
        self.actions_frame = ActionEditorFrame(self) # New Editor Frame
        self.rewards_frame = RewardEditorFrame(self) # New Rewards Frame
        self.elevenlabs_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_elevenlabs_frame()
        self.profiles_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.setup_profiles_frame()

        # Start with Dashboard
        self.show_dashboard_frame()

        # Log Updater
        self.after(100, self.update_logs)

    def _create_linux_desktop_entry(self):
        """Automatically create a .desktop file on Linux if it doesn't exist."""
        if os.name != 'posix' or sys.platform == 'darwin':
            return # Only for Linux
            
        desktop_dir = os.path.expanduser("~/.local/share/applications")
        desktop_file = os.path.join(desktop_dir, "openstreambot.desktop")
        
        if not os.path.exists(desktop_file):
            try:
                os.makedirs(desktop_dir, exist_ok=True)
                base_dir = os.path.dirname(os.path.abspath(__file__))
                icon_path = os.path.join(base_dir, "assets", "logo.png")
                
                # Wenn wir im kompilierten Modus sind, verwenden wir das executable, sonst python
                if getattr(sys, 'frozen', False):
                    python_cmd = os.path.abspath(sys.executable)
                else:
                    venv_python = os.path.join(base_dir, "venv", "bin", "python")
                    if os.path.exists(venv_python):
                        python_cmd = venv_python
                    else:
                        python_cmd = sys.executable

                # Create wrapper script for dumb launchers
                wrapper_script = os.path.join(base_dir, "start_bot.sh")
                if not os.path.exists(wrapper_script):
                    with open(wrapper_script, "w") as f:
                        f.write(f"#!/bin/bash\ncd \"{base_dir}\"\nexec \"{python_cmd}\" \"{os.path.join(base_dir, 'launcher.py')}\"\n")
                    os.chmod(wrapper_script, 0o755)

                content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=OpenStreamBot
Comment=Automatisierungs-Bot für Twitch und YouTube
Exec={wrapper_script}
Path={base_dir}
Icon={icon_path}
Terminal=false
Categories=Utility;
StartupNotify=true
"""
                with open(desktop_file, "w") as f:
                    f.write(content)
                
                # Make the desktop file executable (required by many Linux app launchers)
                os.chmod(desktop_file, 0o755)
                
                # Try to update desktop database
                try:
                    subprocess.run(["update-desktop-database", desktop_dir], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except FileNotFoundError:
                    pass
                print("[System] Registered OpenStreamBot Linux App Shortcut.")
            except Exception as e:
                print(f"[System] Failed to register Linux App Shortcut: {e}")

    def setup_dashboard_frame(self):
        # Header
        self.dash_label = ctk.CTkLabel(self.dashboard_frame, text="Control Center", font=ctk.CTkFont(size=24, weight="bold"))
        self.dash_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Buttons Area Card
        self.btn_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.btn_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        self.start_btn = ctk.CTkButton(self.btn_frame, text="Start Bot", height=32, font=ctk.CTkFont(weight="bold"), command=self.toggle_bot, fg_color="#10B981", hover_color="#059669")
        self.start_btn.pack(side="left", padx=20, pady=20, expand=True)

        self.open_web_btn = ctk.CTkButton(self.btn_frame, text="Open Web Dashboard", height=32, font=ctk.CTkFont(weight="bold"), command=self.open_web_dashboard, fg_color="#3B82F6", hover_color="#2563EB")
        self.open_web_btn.pack(side="left", padx=20, pady=20, expand=True)

        # YouTube Stream Control
        self.yt_connect_btn = ctk.CTkButton(self.btn_frame, text="Connect YouTube Stream", height=32, font=ctk.CTkFont(weight="bold"), command=self.connect_youtube_stream, fg_color="#EF4444", hover_color="#DC2626")
        self.yt_connect_btn.pack(side="left", padx=20, pady=20, expand=True)
        self.yt_connect_btn.configure(state="disabled")

        # Action Queue Overview Card (Above Live Log)
        self.queue_overview_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.queue_overview_frame.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ew")

        q_head = ctk.CTkFrame(self.queue_overview_frame, fg_color="transparent")
        q_head.pack(fill="x", padx=15, pady=(10, 2))
        
        ctk.CTkLabel(q_head, text="⚡ Action Queue Status", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.lbl_queue_summary = ctk.CTkLabel(q_head, text="System Status: Idle", font=ctk.CTkFont(size=11), text_color="gray70")
        self.lbl_queue_summary.pack(side="right")

        self.queue_chips_frame = ctk.CTkFrame(self.queue_overview_frame, fg_color="transparent")
        self.queue_chips_frame.pack(fill="x", padx=15, pady=(0, 10))

        # Console Output Card (Row 3)
        self.console_frame = ctk.CTkFrame(self.dashboard_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.console_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.console_frame.grid_columnconfigure(0, weight=1)
        self.console_frame.grid_rowconfigure(1, weight=1)

        self.console_label = ctk.CTkLabel(self.console_frame, text="Live Log Output", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.console_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.log_textbox = ctk.CTkTextbox(self.console_frame, width=600, height=260, fg_color=("gray90", "gray10"), corner_radius=5)
        self.log_textbox.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        
        # Configure Tags for ANSI Colors
        try:
            tb = self.log_textbox._textbox
            tb.tag_config("red", foreground="#FF5555")
            tb.tag_config("green", foreground="#50FA7B")
            tb.tag_config("yellow", foreground="#F1FA8C")
            tb.tag_config("cyan", foreground="#8BE9FD")
            tb.tag_config("grey", foreground="#6272A4")
            tb.tag_config("reset", foreground="#F8F8F2")
        except:
             pass

        self.dashboard_frame.grid_rowconfigure(3, weight=1)
        self.dashboard_frame.grid_columnconfigure(0, weight=1)

    def update_queue_overview_loop(self):
        try:
            self.refresh_queue_overview()
        except Exception:
            pass
        self.after(1500, self.update_queue_overview_loop)

    def refresh_queue_overview(self):
        if not hasattr(self, 'queue_chips_frame'):
            return

        if not hasattr(self, '_queue_chip_widgets'):
            self._queue_chip_widgets = {}
        if not hasattr(self, '_last_valid_statuses'):
            self._last_valid_statuses = None

        statuses = None
        # 1. Read persisted queue status snapshot from disk (works when bot runs in subprocess)
        status_file = QUEUE_STATUS_FILE
        if not os.path.exists(status_file):
            alt_path = os.path.join(os.getcwd(), ".queue_status.json")
            if os.path.exists(alt_path):
                status_file = alt_path

        if os.path.exists(status_file):
            try:
                with open(status_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        statuses = json.loads(content)
                        self._last_valid_statuses = statuses
            except Exception as e:
                print(f"[Launcher] Error reading status from {status_file}: {e}")
        else:
            print(f"[Launcher Queue Debug] Status file not found at: {status_file} (CWD: {os.getcwd()})")

        if not statuses and self._last_valid_statuses:
            statuses = self._last_valid_statuses

        # 2. Fallback to in-process ActionEngine instance
        if not statuses:
            engine = getattr(self, 'action_engine', None)
            if not engine and hasattr(self, 'actions_frame'):
                engine = getattr(self.actions_frame, 'action_engine', None)
            if engine:
                statuses = engine.get_all_queues_status()
                self._last_valid_statuses = statuses

        # 3. Default fallback
        if not statuses:
            statuses = {
                "Default": {"name": "Default", "pending": 0, "status": "Idle", "paused": False, "last_action": None},
                "TTS": {"name": "TTS", "pending": 0, "status": "Idle", "paused": False, "last_action": None},
                "Overlays": {"name": "Overlays", "pending": 0, "status": "Idle", "paused": False, "last_action": None},
                "SoundFX": {"name": "SoundFX", "pending": 0, "status": "Idle", "paused": False, "last_action": None},
            }

        total_pending = sum(s.get("pending", 0) for s in statuses.values())
        any_running = any(s.get("status") == "Running" for s in statuses.values())
        
        if any_running:
            self.lbl_queue_summary.configure(text=f"⚡ Active Execution | Pending: {total_pending}", text_color="#10B981")
        elif total_pending > 0:
            self.lbl_queue_summary.configure(text=f"⏳ Queued: {total_pending}", text_color="#F59E0B")
        else:
            self.lbl_queue_summary.configure(text="System Status: Idle", text_color="gray70")

        # Clean up chips for removed queues
        existing_keys = set(self._queue_chip_widgets.keys())
        current_keys = set(statuses.keys())
        for removed_key in (existing_keys - current_keys):
            chip, _ = self._queue_chip_widgets.pop(removed_key)
            chip.destroy()

        for q_name, data in statuses.items():
            st = data.get("status", "Idle")
            pending = data.get("pending", 0)
            paused = data.get("paused", False)
            last = data.get("last_action")
            
            if paused:
                badge_bg = "#B45309"
                badge_txt = f"{q_name}: ⏸ Paused"
            elif st == "Running":
                badge_bg = "#047857"
                cur = data.get("current_action", "")
                badge_txt = f"{q_name}: ▶ '{cur}'" + (f" (+{pending})" if pending > 0 else "")
            elif pending > 0:
                badge_bg = "#1D4ED8"
                badge_txt = f"{q_name}: ⏳ {pending} pending"
            else:
                badge_bg = ("gray75", "#262626")
                if last:
                    badge_txt = f"{q_name}: Idle (Zuletzt: '{last}')"
                else:
                    badge_txt = f"{q_name}: Idle"

            text_col = "white" if badge_bg != ("gray75", "#262626") else ("gray10", "gray80")

            if q_name not in self._queue_chip_widgets:
                chip = ctk.CTkFrame(self.queue_chips_frame, fg_color=badge_bg, corner_radius=6)
                chip.pack(side="left", padx=4, pady=2)
                lbl = ctk.CTkLabel(chip, text=badge_txt, font=ctk.CTkFont(size=11, weight="bold"), text_color=text_col)
                lbl.pack(padx=8, pady=3)
                self._queue_chip_widgets[q_name] = (chip, lbl)
            else:
                chip, lbl = self._queue_chip_widgets[q_name]
                chip.configure(fg_color=badge_bg)
                lbl.configure(text=badge_txt, text_color=text_col)

    # --- STRUCTURED SETTINGS SCREEN ---
    def setup_settings_frame(self):
        self.settings_label = ctk.CTkLabel(self.settings_frame, text="Configuration", font=ctk.CTkFont(size=24, weight="bold"))
        self.settings_label.grid(row=0, column=0, padx=20, pady=(20, 2), sticky="w")

        ctk.CTkLabel(self.settings_frame, text="Passe die Einstellungen für Twitch, YouTube, OBS und Audio an.", text_color="gray70").grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        self.settings_scroll = ctk.CTkScrollableFrame(self.settings_frame, fg_color="transparent")
        self.settings_scroll.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")

        self.settings_frame.grid_rowconfigure(2, weight=1)
        self.settings_frame.grid_columnconfigure(0, weight=1)

        # Variables mapping to config.yaml
        self.cfg_vars = {
            "server_host": ctk.StringVar(value="localhost"),
            "server_port": ctk.StringVar(value="8080"),

            "twitch_enabled": ctk.BooleanVar(value=True),
            "twitch_channel": ctk.StringVar(value=""),
            "twitch_client_id": ctk.StringVar(value=""),
            "twitch_client_secret": ctk.StringVar(value=""),
            "twitch_redirect_uri": ctk.StringVar(value="http://localhost:8080"),

            "youtube_enabled": ctk.BooleanVar(value=True),
            "youtube_client_secret_file": ctk.StringVar(value="client_secret.json"),
            "youtube_token_file": ctk.StringVar(value="token_youtube.json"),

            "obs_enabled": ctk.BooleanVar(value=True),
            "obs_host": ctk.StringVar(value="localhost"),
            "obs_port": ctk.StringVar(value="4455"),
            "obs_password": ctk.StringVar(value=""),

            "vol_sfx": ctk.StringVar(value="1.0"),
            "vol_playlist": ctk.StringVar(value="0.5"),
        }

        # Card 1: Server
        self._build_settings_card(self.settings_scroll, "🌐 Server Settings", [
            ("Server Host:", self.cfg_vars["server_host"], "localhost"),
            ("Server Port:", self.cfg_vars["server_port"], "8080"),
        ])

        # Card 2: Twitch
        card_tw = self._create_card_frame(self.settings_scroll, "💜 Twitch Configuration")
        ctk.CTkSwitch(card_tw, text="Twitch Bot aktivieren", variable=self.cfg_vars["twitch_enabled"]).pack(anchor="w", padx=15, pady=(5, 10))
        self._add_field_row(card_tw, "Kanal Name:", self.cfg_vars["twitch_channel"], "Dein Twitch Username")
        self._add_field_row(card_tw, "Client ID:", self.cfg_vars["twitch_client_id"], "Twitch Developer App Client ID")
        self._add_field_row(card_tw, "Client Secret:", self.cfg_vars["twitch_client_secret"], "Twitch App Client Secret", show="*")
        self._add_field_row(card_tw, "Redirect URI:", self.cfg_vars["twitch_redirect_uri"], "http://localhost:8080")

        # Card 3: YouTube
        card_yt = self._create_card_frame(self.settings_scroll, "🔴 YouTube Configuration")
        ctk.CTkSwitch(card_yt, text="YouTube Bot aktivieren", variable=self.cfg_vars["youtube_enabled"]).pack(anchor="w", padx=15, pady=(5, 10))
        self._add_field_row(card_yt, "Client Secret File:", self.cfg_vars["youtube_client_secret_file"], "client_secret.json")
        self._add_field_row(card_yt, "Token File:", self.cfg_vars["youtube_token_file"], "token_youtube.json")

        # Card 4: OBS WebSocket
        card_obs = self._create_card_frame(self.settings_scroll, "🎥 OBS Studio WebSocket Integration")
        ctk.CTkSwitch(card_obs, text="OBS Integration aktivieren", variable=self.cfg_vars["obs_enabled"]).pack(anchor="w", padx=15, pady=(5, 10))
        self._add_field_row(card_obs, "OBS Host:", self.cfg_vars["obs_host"], "localhost")
        self._add_field_row(card_obs, "OBS Port:", self.cfg_vars["obs_port"], "4455")
        self._add_field_row(card_obs, "Passwort:", self.cfg_vars["obs_password"], "OBS WebSocket Passwort", show="*")

        # Card 5: Audio
        self._build_settings_card(self.settings_scroll, "🔊 Audio & Lautstärke", [
            ("SFX Lautstärke (0.0-1.0):", self.cfg_vars["vol_sfx"], "1.0"),
            ("Playlist Lautstärke (0.0-1.0):", self.cfg_vars["vol_playlist"], "0.5"),
        ])

        # Bottom Actions Bar
        self.settings_btn_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.settings_btn_frame.grid(row=3, column=0, padx=20, pady=15, sticky="ew")

        ctk.CTkButton(self.settings_btn_frame, text="💾 Speichern", command=self.save_config_from_ui, fg_color="#10B981", hover_color="#059669", height=36, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=5)
        ctk.CTkButton(self.settings_btn_frame, text="🔄 Neuladen", command=self.load_config_to_ui, fg_color="#6B7280", hover_color="#4B5563", height=36).pack(side="right", padx=5)
        ctk.CTkButton(self.settings_btn_frame, text="📝 Editor (Raw YAML)", command=self.open_raw_yaml_editor, fg_color="#3B82F6", hover_color="#2563EB", height=36).pack(side="left", padx=5)

        self.load_config_to_ui()
        bind_universal_scroll(self.settings_scroll)

    def _create_card_frame(self, parent, title):
        card = ctk.CTkFrame(parent, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        card.pack(fill="x", pady=8, padx=5)
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(12, 6))
        return card

    def _add_field_row(self, card, label_text, string_var, placeholder="", show=None):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(row, text=label_text, width=160, anchor="w").pack(side="left")
        kwargs = {"textvariable": string_var, "placeholder_text": placeholder}
        if show: kwargs["show"] = show
        entry = ctk.CTkEntry(row, **kwargs)
        entry.pack(side="left", fill="x", expand=True)

    def _build_settings_card(self, parent, title, fields):
        card = self._create_card_frame(parent, title)
        for lbl, var, ph in fields:
            self._add_field_row(card, lbl, var, ph)

    # --- ACCOUNTS FRAME ---
    def setup_accounts_frame(self):
        self.acc_label = ctk.CTkLabel(self.accounts_frame, text="Manage Accounts", font=ctk.CTkFont(size=24, weight="bold"))
        self.acc_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")

        # Twitch Section Card
        self.twitch_frame = ctk.CTkFrame(self.accounts_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.twitch_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.twitch_frame, text="Twitch", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=20, pady=15)
        self.twitch_status = ctk.CTkLabel(self.twitch_frame, text="Checking...", font=ctk.CTkFont(weight="bold"), text_color="gray")
        self.twitch_status.grid(row=0, column=1, padx=20)
        
        self.btn_twitch_login = ctk.CTkButton(self.twitch_frame, text="Login with Twitch", command=self.login_twitch, fg_color="#9146FF", hover_color="#772CE8")
        self.btn_twitch_login.grid(row=0, column=2, padx=10, pady=15)
        
        self.btn_twitch_logout = ctk.CTkButton(self.twitch_frame, text="Logout", command=self.logout_twitch, fg_color="red", hover_color="darkred")
        self.btn_twitch_logout.grid(row=0, column=3, padx=10, pady=15)

        # YouTube Section Card
        self.yt_frame = ctk.CTkFrame(self.accounts_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.yt_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.yt_frame, text="YouTube", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, padx=20, pady=15)
        self.yt_status = ctk.CTkLabel(self.yt_frame, text="Checking...", font=ctk.CTkFont(weight="bold"), text_color="gray")
        self.yt_status.grid(row=0, column=1, padx=20)
        
        self.btn_yt_login = ctk.CTkButton(self.yt_frame, text="Login with Google", command=self.login_youtube, fg_color="#FF0000", hover_color="#CC0000")
        self.btn_yt_login.grid(row=0, column=2, padx=10, pady=15)

        self.btn_yt_logout = ctk.CTkButton(self.yt_frame, text="Logout", command=self.logout_youtube, fg_color="red", hover_color="darkred")
        self.btn_yt_logout.grid(row=0, column=3, padx=10, pady=15)
        
        # Sync Button
        self.btn_yt_sync = ctk.CTkButton(self.yt_frame, text="Sync Shorts", command=self.sync_shorts, fg_color="#F59E0B", hover_color="#D97706")
        self.btn_yt_sync.grid(row=0, column=4, padx=10, pady=15)
        
        # Overlay URL Info
        ctk.CTkLabel(self.yt_frame, text="Overlay URL:").grid(row=1, column=0, padx=20, pady=(0, 15), sticky="e")
        self.ent_overlay_url = ctk.CTkEntry(self.yt_frame, width=300)
        self.ent_overlay_url.insert(0, "http://localhost:8000/interface/yt_overlay.html")
        self.ent_overlay_url.configure(state="readonly")
        self.ent_overlay_url.grid(row=1, column=1, columnspan=3, padx=10, pady=(0, 15), sticky="ew")
        
        ctk.CTkButton(self.yt_frame, text="Copy", width=60, command=self.copy_overlay_url).grid(row=1, column=4, padx=10, pady=(0, 15))


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

    def _hide_all_frames(self):
        self.dashboard_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.accounts_frame.grid_forget()
        self.actions_frame.grid_forget()
        self.rewards_frame.grid_forget()
        self.profiles_frame.grid_forget()
        if hasattr(self, 'elevenlabs_frame'): self.elevenlabs_frame.grid_forget()

    def show_dashboard_frame(self):
        self._hide_all_frames()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")

    def show_settings_frame(self):
        self._hide_all_frames()
        self.settings_frame.grid(row=0, column=1, sticky="nsew")
        self.load_config_to_ui()

    def show_accounts_frame(self):
        self._hide_all_frames()
        self.accounts_frame.grid(row=0, column=1, sticky="nsew")
        self.update_account_status()

    def show_actions_frame(self):
        self._hide_all_frames()
        self.actions_frame.grid(row=0, column=1, sticky="nsew")

    def show_rewards_frame(self):
        self._hide_all_frames()
        self.rewards_frame.grid(row=0, column=1, sticky="nsew")
        self.rewards_frame.load_creds() # Refresh creds if changed
        self.rewards_frame.refresh_rewards() # Refresh list

    def show_profiles_frame(self):
        self._hide_all_frames()
        self.profiles_frame.grid(row=0, column=1, sticky="nsew")
        self.refresh_profile_list()

    def show_elevenlabs_frame(self):
        self._hide_all_frames()
        self.elevenlabs_frame.grid(row=0, column=1, sticky="nsew")

    def setup_profiles_frame(self):
        self.prof_label = ctk.CTkLabel(self.profiles_frame, text="Profile Manager", font=ctk.CTkFont(size=24, weight="bold"))
        self.prof_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Helper Text
        ctk.CTkLabel(self.profiles_frame, text="Profiles allow you to switch between different bot configurations.", text_color="gray").grid(row=1, column=0, padx=20, sticky="w")
        
        # Content Area
        self.prof_content = ctk.CTkFrame(self.profiles_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.prof_content.grid(row=2, column=0, padx=20, pady=20, sticky="nsew")
        
        # List
        self.prof_listbox = ctk.CTkScrollableFrame(self.prof_content, width=300, height=300, fg_color="transparent")
        self.prof_listbox.pack(side="left", fill="y", padx=10, pady=10)
        
        # Controls
        self.prof_controls = ctk.CTkFrame(self.prof_content, fg_color="transparent")
        self.prof_controls.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(self.prof_controls, text="Enter Profile Name:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,5))
        self.entry_profile = ctk.CTkEntry(self.prof_controls)
        self.entry_profile.pack(pady=5, fill="x")
        
        self.btn_create_prof = ctk.CTkButton(self.prof_controls, text="Save Current as New Profile", command=self.create_profile, fg_color="#3B82F6", hover_color="#2563EB")
        self.btn_create_prof.pack(pady=10, fill="x")
        
        self.btn_save_prof = ctk.CTkButton(self.prof_controls, text="Overwrite Selected Profile", fg_color="#F59E0B", hover_color="#D97706", command=self.save_to_selected_profile)
        self.btn_save_prof.pack(pady=10, fill="x")
        
        self.btn_load_prof = ctk.CTkButton(self.prof_controls, text="Load Selected Profile", fg_color="#10B981", hover_color="#059669", command=self.load_selected_profile)
        self.btn_load_prof.pack(pady=10, fill="x")
        
        self.btn_del_prof = ctk.CTkButton(self.prof_controls, text="Delete Selected Profile", fg_color="#EF4444", hover_color="#DC2626", command=self.delete_selected_profile)
        self.btn_del_prof.pack(pady=10, fill="x")

        # Full Backup System Section
        ctk.CTkLabel(self.prof_controls, text="Full Backup System (.osbbackup):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(15, 5))

        self.btn_export_backup = ctk.CTkButton(self.prof_controls, text="📦 Export Full Backup", fg_color="#8B5CF6", hover_color="#7C3AED", command=self.export_full_backup)
        self.btn_export_backup.pack(pady=5, fill="x")

        self.btn_import_backup = ctk.CTkButton(self.prof_controls, text="📥 Import Full Backup Archive", fg_color="#6366F1", hover_color="#4F46E5", command=self.import_full_backup)
        self.btn_import_backup.pack(pady=5, fill="x")
        
        self.selected_profile_btn = None
        self.selected_profile_name = None

    def refresh_profile_list(self):
        for w in self.prof_listbox.winfo_children(): w.destroy()
        
        profiles = self.profile_manager.get_profiles()
        for p in profiles:
            btn = ctk.CTkButton(self.prof_listbox, text=p, command=lambda n=p: self.select_profile(n),
                                fg_color="transparent", border_width=1, text_color=("gray10", "gray90"))
            btn.pack(fill="x", pady=2)
        bind_universal_scroll(self.prof_listbox)
            
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

    def export_full_backup(self):
        from tkinter import filedialog
        prof_name = self.selected_profile_name or self.entry_profile.get() or "Default"
        filepath = filedialog.asksaveasfilename(
            title="Export Full Profile Backup",
            defaultextension=".osbbackup",
            filetypes=[("OpenStreamBot Backup", "*.osbbackup"), ("Zip Archives", "*.zip")],
            initialfile=f"backup_{prof_name}.osbbackup"
        )
        if not filepath:
            return
        
        try:
            from core.backup_manager import BackupManager
            bm = BackupManager()
            out_file = bm.export_backup(profile_name=prof_name, export_filepath=filepath)
            messagebox.showinfo("Export Successful", f"Full backup successfully exported to:\n{out_file}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export backup: {e}")

    def import_full_backup(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            title="Import Full Profile Backup",
            filetypes=[("OpenStreamBot Backup", "*.osbbackup"), ("Zip Archives", "*.zip"), ("All Files", "*.*")]
        )
        if not filepath:
            return
            
        try:
            from core.backup_manager import BackupManager
            bm = BackupManager()
            imported_name = bm.import_backup(filepath)
            self.refresh_profile_list()
            messagebox.showinfo("Import Successful", f"Full backup imported successfully as profile '{imported_name}'!")
        except Exception as e:
            messagebox.showerror("Import Failed", f"Failed to import backup: {e}")

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
        if not hasattr(self, 'cfg_vars'):
            return

        cfg = {}
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    cfg = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[Launcher] Error reading config.yaml: {e}")

        # Populate GUI Variables
        srv = cfg.get("server", {})
        self.cfg_vars["server_host"].set(str(srv.get("host", "localhost")))
        self.cfg_vars["server_port"].set(str(srv.get("port", 8080)))

        tw = cfg.get("twitch", {})
        self.cfg_vars["twitch_enabled"].set(bool(tw.get("enabled", True)))
        self.cfg_vars["twitch_channel"].set(str(tw.get("channel", "")))
        self.cfg_vars["twitch_client_id"].set(str(tw.get("client_id", "")))
        self.cfg_vars["twitch_client_secret"].set(str(tw.get("client_secret", "")))
        self.cfg_vars["twitch_redirect_uri"].set(str(tw.get("redirect_uri", "http://localhost:8080")))

        yt = cfg.get("youtube", {})
        self.cfg_vars["youtube_enabled"].set(bool(yt.get("enabled", True)))
        self.cfg_vars["youtube_client_secret_file"].set(str(yt.get("client_secret_file", "client_secret.json")))
        self.cfg_vars["youtube_token_file"].set(str(yt.get("token_file", "token_youtube.json")))

        obs = cfg.get("obs", {})
        self.cfg_vars["obs_enabled"].set(bool(obs.get("enabled", True)))
        self.cfg_vars["obs_host"].set(str(obs.get("host", "localhost")))
        self.cfg_vars["obs_port"].set(str(obs.get("port", 4455)))
        self.cfg_vars["obs_password"].set(str(obs.get("password", "")))

        vol = cfg.get("audio", {})
        self.cfg_vars["vol_sfx"].set(str(vol.get("sfx", 1.0)))
        self.cfg_vars["vol_playlist"].set(str(vol.get("playlist", 0.5)))

    def save_config_from_ui(self):
        if not hasattr(self, 'cfg_vars'):
            return

        cfg = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg = yaml.safe_load(f) or {}
            except Exception:
                cfg = {}

        if "server" not in cfg or not isinstance(cfg["server"], dict): cfg["server"] = {}
        cfg["server"]["host"] = self.cfg_vars["server_host"].get().strip()
        try: cfg["server"]["port"] = int(self.cfg_vars["server_port"].get().strip() or 8080)
        except: cfg["server"]["port"] = 8080

        if "twitch" not in cfg or not isinstance(cfg["twitch"], dict): cfg["twitch"] = {}
        cfg["twitch"]["enabled"] = self.cfg_vars["twitch_enabled"].get()
        cfg["twitch"]["channel"] = self.cfg_vars["twitch_channel"].get().strip()
        cfg["twitch"]["client_id"] = self.cfg_vars["twitch_client_id"].get().strip()
        cfg["twitch"]["client_secret"] = self.cfg_vars["twitch_client_secret"].get().strip()
        cfg["twitch"]["redirect_uri"] = self.cfg_vars["twitch_redirect_uri"].get().strip() or "http://localhost:8080"

        if "youtube" not in cfg or not isinstance(cfg["youtube"], dict): cfg["youtube"] = {}
        cfg["youtube"]["enabled"] = self.cfg_vars["youtube_enabled"].get()
        cfg["youtube"]["client_secret_file"] = self.cfg_vars["youtube_client_secret_file"].get().strip() or "client_secret.json"
        cfg["youtube"]["token_file"] = self.cfg_vars["youtube_token_file"].get().strip() or "token_youtube.json"

        if "obs" not in cfg or not isinstance(cfg["obs"], dict): cfg["obs"] = {}
        cfg["obs"]["enabled"] = self.cfg_vars["obs_enabled"].get()
        cfg["obs"]["host"] = self.cfg_vars["obs_host"].get().strip() or "localhost"
        try: cfg["obs"]["port"] = int(self.cfg_vars["obs_port"].get().strip() or 4455)
        except: cfg["obs"]["port"] = 4455
        cfg["obs"]["password"] = self.cfg_vars["obs_password"].get().strip()

        if "audio" not in cfg or not isinstance(cfg["audio"], dict): cfg["audio"] = {}
        try: cfg["audio"]["sfx"] = float(self.cfg_vars["vol_sfx"].get().strip() or 1.0)
        except: cfg["audio"]["sfx"] = 1.0
        try: cfg["audio"]["playlist"] = float(self.cfg_vars["vol_playlist"].get().strip() or 0.5)
        except: cfg["audio"]["playlist"] = 0.5

        try:
            with open(CONFIG_FILE, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False, sort_keys=False)
            messagebox.showinfo("Erfolg", "Konfiguration erfolgreich gespeichert!")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern der Konfiguration:\n{e}")

    def open_raw_yaml_editor(self):
        """Opens a raw YAML text editor modal for power users."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("Raw YAML Config Editor")
        dlg.geometry("700x500")

        ctk.CTkLabel(dlg, text="Raw config.yaml Editor", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        txt = ctk.CTkTextbox(dlg, width=650, height=380, fg_color=("gray90", "gray10"))
        txt.pack(fill="both", expand=True, padx=15, pady=10)

        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    txt.insert("0.0", f.read())
        except Exception as e:
            txt.insert("0.0", f"# Error reading config: {e}")

        btn_bar = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=10)

        def save_raw():
            raw_val = txt.get("0.0", "end")
            try:
                yaml.safe_load(raw_val)
                with open(CONFIG_FILE, "w") as f:
                    f.write(raw_val)
                self.load_config_to_ui()
                dlg.destroy()
                messagebox.showinfo("Erfolg", "Raw YAML Konfiguration gespeichert!")
            except yaml.YAMLError as ye:
                messagebox.showerror("YAML Fehler", f"Ungültiges YAML Format:\n{ye}")

        ctk.CTkButton(btn_bar, text="Speichern & Schließen", command=save_raw, fg_color="#10B981", hover_color="#059669").pack(side="right", padx=5)
        ctk.CTkButton(btn_bar, text="Abbrechen", command=dlg.destroy, fg_color="#6B7280", hover_color="#4B5563").pack(side="right", padx=5)

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
             base_dir = os.path.dirname(os.path.abspath(__file__))
        
        try:
            # Start process properly
            self.bot_process = subprocess.Popen(
                cmd,
                cwd=base_dir,
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

    def setup_elevenlabs_frame(self):
        self.el_label = ctk.CTkLabel(self.elevenlabs_frame, text="Elevenlabs Configuration", font=ctk.CTkFont(size=24, weight="bold"))
        self.el_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        # Config section
        self.el_config = ctk.CTkFrame(self.elevenlabs_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.el_config.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Config Read/Set Initial Check state
        is_enabled = False
        api_key_val = ""
        max_chars_val = "200"

        try:
            with open(CONFIG_FILE, "r") as f:
                 cfg = yaml.safe_load(f)
                 el = cfg.get('elevenlabs', {})
                 is_enabled = el.get('enabled', False)
                 api_key_val = el.get('api_key', '')
                 max_chars_val = str(el.get('max_chars', '200'))
        except:
            pass

        self.chkbx_elevenlabs_enabled = ctk.CTkCheckBox(self.el_config, text="Enable Elevenlabs Integration")
        self.chkbx_elevenlabs_enabled.grid(row=0, column=0, columnspan=2, padx=15, pady=15, sticky="w")
        if is_enabled:
            self.chkbx_elevenlabs_enabled.select()

        ctk.CTkLabel(self.el_config, text="API Key:").grid(row=1, column=0, padx=15, pady=5, sticky="w")
        self.ent_el_apikey = ctk.CTkEntry(self.el_config, width=300, show="*")
        self.ent_el_apikey.insert(0, api_key_val)
        self.ent_el_apikey.grid(row=1, column=1, padx=15, pady=5, sticky="w")

        ctk.CTkLabel(self.el_config, text="Max Characters limit per action:").grid(row=2, column=0, padx=15, pady=5, sticky="w")
        self.ent_el_limit = ctk.CTkEntry(self.el_config, width=100)
        self.ent_el_limit.insert(0, max_chars_val)
        self.ent_el_limit.grid(row=2, column=1, padx=15, pady=5, sticky="w")

        self.btn_el_save = ctk.CTkButton(self.el_config, text="Save Config", command=self.save_elevenlabs_config, fg_color="#10B981", hover_color="#059669")
        self.btn_el_save.grid(row=3, column=0, columnspan=2, padx=15, pady=15, sticky="w")

        # Voice fetching section
        self.el_voices_frame = ctk.CTkFrame(self.elevenlabs_frame, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.el_voices_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        self.btn_el_fetch_voices = ctk.CTkButton(self.el_voices_frame, text="Fetch Voice List", command=self.fetch_elevenlabs_voices, fg_color="#3B82F6", hover_color="#2563EB")
        self.btn_el_fetch_voices.grid(row=0, column=0, padx=15, pady=15, sticky="w")
        
        self.el_voices_textbox = ctk.CTkTextbox(self.el_voices_frame, width=600, height=300, fg_color=("gray90", "gray10"), corner_radius=5)
        self.el_voices_textbox.grid(row=1, column=0, padx=15, pady=(0,15), sticky="nsew")

    def save_elevenlabs_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = yaml.safe_load(f)
            if 'elevenlabs' not in cfg:
                cfg['elevenlabs'] = {}
                
            cfg['elevenlabs']['enabled'] = bool(self.chkbx_elevenlabs_enabled.get())
            cfg['elevenlabs']['api_key'] = self.ent_el_apikey.get()
            try:
                cfg['elevenlabs']['max_chars'] = int(self.ent_el_limit.get())
            except:
                cfg['elevenlabs']['max_chars'] = 200 # fallback
                
            with open(CONFIG_FILE, "w") as f:
                yaml.dump(cfg, f)
                
            messagebox.showinfo("Success", "Elevenlabs Config saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def fetch_elevenlabs_voices(self):
        api_key = self.ent_el_apikey.get()
        if not api_key:
             messagebox.showerror("Error", "Please provide an API Key first!")
             return
             
        self.el_voices_textbox.delete("0.0", "end")
        self.el_voices_textbox.insert("end", "Fetching voices...\n")
        
        def do_fetch():
            import asyncio
            from platforms.elevenlabs_tts import ElevenLabsTTS
            tts = ElevenLabsTTS(api_key=api_key)
            voices = asyncio.run(tts.fetch_voices())
            
            def update_ui():
                self.el_voices_textbox.delete("0.0", "end")
                if not voices:
                    self.el_voices_textbox.insert("end", "No voices found or invalid API key.\n")
                    return
                for v in voices:
                    self.el_voices_textbox.insert("end", f"Name: {v['name']}  |  Category: {v['category']}\nVoice ID: {v['voice_id']}\n-----------------------------------\n")
            
            self.after(0, update_ui)
            
        threading.Thread(target=do_fetch, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
