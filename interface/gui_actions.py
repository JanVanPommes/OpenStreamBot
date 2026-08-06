import customtkinter as ctk
from tkinter import messagebox, simpledialog, filedialog
import yaml
import os
import pygame._sdl2.audio as sdl_audio
import pygame

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Display Name Mappings (Deutsch) ---
TRIGGER_DISPLAY_NAMES = {
    "twitch_command": "💬 Twitch: Chat-Befehl",
    "youtube_command": "📺 YouTube: Chat-Befehl",
    "twitch_raid": "⚔️ Twitch: Raid empfangen",
    "twitch_sub": "⭐ Twitch: Neuer Subscriber",
    "twitch_redemption": "💎 Twitch: Kanalpunkt-Einlösung",
    "twitch_first_message": "👋 Twitch: Erste Nachricht",
    "youtube_first_message": "👋 YouTube: Erste Nachricht",
    "twitch_watch_streak": "🔥 Twitch: Zuschauerserie",
    "youtube_new_member": "🎉 YouTube: Neues Mitglied",
    "youtube_member_milestone": "🏅 YouTube: Mitglieder-Jubiläum",
    "youtube_super_chat": "💰 YouTube: Super Chat",
    "timer": "⏱️ Timer (Intervall)",
    "obs_scene": "🎬 OBS: Szene gewechselt",
}

SUB_ACTION_DISPLAY_NAMES = {
    "twitch_chat": "💬 Chat-Nachricht (Twitch)",
    "youtube_chat": "📺 YouTube Nachricht",
    "twitch_command": "⚡ Twitch Befehl ausführen",
    "delay": "⏳ Verzögerung",
    "log": "📝 Log-Nachricht",
    "play_sound": "🔊 Sound abspielen",
    "stop_sounds": "🔇 Alle Sounds stoppen",
    "playlist": "🎵 Playlist starten",
    "stop_playlist": "⏹️ Playlist stoppen",
    "obs_set_scene": "🎬 OBS Szene wechseln",
    "youtube_random_short": "📱 YouTube Short abspielen",
    "trigger_action": "🔗 Action auslösen",
    "set_volume": "🔈 Lautstärke ändern",
    "set_action_state": "🔀 Action-Status ändern",
    "twitch_create_clip": "🎬 Twitch Clip erstellen",
    "twitch_enable_reward": "💎 Twitch: Reward aktivieren",
    "twitch_disable_reward": "💎 Twitch: Reward deaktivieren",
    "execute_csharp": "💻 C# Code ausführen",
    "random_action_group": "🎲 Zufalls-Gruppe",
    "elevenlabs_tts": "🗣️ Text-to-Speech (ElevenLabs)",
}

# Context variables available per trigger type
TRIGGER_CONTEXT_VARS = {
    "twitch_command": ["%user%", "%message%"],
    "youtube_command": ["%user%", "%message%"],
    "twitch_raid": ["%user%", "%message%"],
    "twitch_sub": ["%user%", "%message%"],
    "twitch_redemption": ["%user%", "%input%", "%message%"],
    "twitch_first_message": ["%user%", "%message%"],
    "youtube_first_message": ["%user%", "%message%"],
    "twitch_watch_streak": ["%user%", "%message%", "%streak_count%"],
    "youtube_new_member": ["%user%", "%message%"],
    "youtube_member_milestone": ["%user%", "%message%", "%months%", "%user_message%"],
    "youtube_super_chat": ["%user%", "%message%", "%amount%", "%currency%", "%user_message%"],
    "timer": [],
    "obs_scene": [],
}

def get_ws_url():
    port = 8080 # Default fallback
    if os.path.exists("config.yaml"):
        try:
            with open("config.yaml", "r") as f:
                cfg = yaml.safe_load(f)
                port = cfg.get('server', {}).get('port', 8080)
        except: pass
    return f"ws://localhost:{port}"

class ActionEditorFrame(ctk.CTkFrame):
    def __init__(self, master, config_file="actions.yaml"):
        super().__init__(master)
        self.config_file = config_file
        self.actions = []
        self.current_action = None
        self.collapsed_groups = self._load_collapsed_groups()
        
        # Color palette for groups (rotating)
        self._group_colors = [
            "#3B82F6",  # Blue
            "#10B981",  # Green
            "#F59E0B",  # Amber
            "#EF4444",  # Red
            "#8B5CF6",  # Violet
            "#EC4899",  # Pink
            "#06B6D4",  # Cyan
            "#F97316",  # Orange
        ]
        
        self.load_actions()
        
        # --- LAYOUT ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # LEFT SIDE: Action List
        self.left_panel = ctk.CTkFrame(self, width=220)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.left_panel.grid_rowconfigure(1, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_propagate(False)
        
        ctk.CTkLabel(self.left_panel, text="Actions", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=5)
        
        self.action_listbox = ctk.CTkScrollableFrame(self.left_panel, width=200)
        self.action_listbox.grid(row=1, column=0, sticky="nsew", padx=5)
        
        self.btn_add_action = ctk.CTkButton(self.left_panel, text="+ New Action", command=self.add_action)
        self.btn_add_action.grid(row=2, column=0, pady=10, padx=10)
        
        self.btn_delete_action = ctk.CTkButton(self.left_panel, text="Delete Action", fg_color="red", command=self.delete_current_action)
        self.btn_delete_action.grid(row=3, column=0, pady=(0, 10), padx=10)

        # RIGHT SIDE: Editor
        self.editor_panel = ctk.CTkFrame(self)
        self.editor_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.editor_panel.grid_columnconfigure(0, weight=1)
        self.editor_panel.grid_columnconfigure(1, weight=1)
        self.editor_panel.grid_rowconfigure(2, weight=1) # Subactions take space

        # Editor Header (Name + Group)
        self.header_frame = ctk.CTkFrame(self.editor_panel, fg_color=("gray85", "#333333"), border_width=1, border_color=("gray75", "#444444"), corner_radius=10)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        self.var_action_name = ctk.StringVar()
        self.entry_name = ctk.CTkEntry(self.header_frame, textvariable=self.var_action_name, font=ctk.CTkFont(size=16, weight="bold"), placeholder_text="Action Name")
        self.entry_name.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.var_action_group = ctk.StringVar()
        self.combo_group = ctk.CTkComboBox(self.header_frame, variable=self.var_action_group, width=120, values=["General"])
        self.combo_group.pack(side="right", padx=5)
        
        # Bind traces for live list update
        self.var_action_name.trace_add("write", lambda *args: self.on_header_change())
        self.var_action_group.trace_add("write", lambda *args: self.on_header_change())
        
        # Cooldown
        self.var_cooldown = ctk.StringVar()
        ctk.CTkLabel(self.header_frame, text="CD (s):").pack(side="right", padx=2)
        self.entry_cooldown = ctk.CTkEntry(self.header_frame, textvariable=self.var_cooldown, width=50)
        self.entry_cooldown.pack(side="right", padx=2)
        
        # Queue Selection + Config Button
        self.var_queue = ctk.StringVar(value="Default")
        ctk.CTkLabel(self.header_frame, text="Queue:").pack(side="right", padx=(5, 2))
        self.combo_queue = ctk.CTkComboBox(self.header_frame, variable=self.var_queue, width=100, values=["Default", "Parallel", "TTS", "Overlays", "SoundFX"])
        self.combo_queue.pack(side="right", padx=2)
        self.var_queue.trace_add("write", lambda *args: self.on_header_change())

        self.btn_test_action = ctk.CTkButton(self.header_frame, text="▶ Testen", width=65, fg_color="#10B981", hover_color="#059669", command=self.test_current_action)
        self.btn_test_action.pack(side="right", padx=4)

        self.btn_manage_queues = ctk.CTkButton(self.header_frame, text="⚙ Queues", width=65, fg_color="#6366F1", hover_color="#4F46E5", command=self.open_queue_manager)
        self.btn_manage_queues.pack(side="right", padx=4)

        # Enabled Switch
        self.var_enabled = ctk.BooleanVar(value=True)
        self.switch_enabled = ctk.CTkSwitch(self.header_frame, text="Active", variable=self.var_enabled, width=60, command=self.on_hot_switch_toggle)
        self.switch_enabled.pack(side="right", padx=10)
        
        # Triggers Section
        self.frame_triggers_container = ctk.CTkFrame(self.editor_panel, fg_color=("gray85", "#262626"), border_width=1, border_color=("gray75", "#333333"), corner_radius=10)
        self.frame_triggers_container.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        self.editor_panel.grid_rowconfigure(1, weight=1) # Allow triggers to expand
        
        ctk.CTkLabel(self.frame_triggers_container, text="Triggers", font=ctk.CTkFont(weight="bold")).pack(side="top", anchor="w", padx=15, pady=(10, 0))

        # Bottom Button Frame
        triggers_btn_frame = ctk.CTkFrame(self.frame_triggers_container, fg_color="transparent")
        triggers_btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        
        self.btn_add_trigger = ctk.CTkButton(triggers_btn_frame, text="+ Add Trigger", height=32, font=ctk.CTkFont(weight="bold"), fg_color="#3B82F6", hover_color="#2563EB", command=self.add_trigger_dialog)
        self.btn_add_trigger.pack(fill="x")

        # IMPORTANT: Create scroll frame after bottom buttons to fix layout squash
        self.scroll_triggers = ctk.CTkScrollableFrame(self.frame_triggers_container, fg_color="transparent")
        self.scroll_triggers.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Context Variables Info (between Triggers and Sub-Actions)
        self.frame_vars = ctk.CTkFrame(self.editor_panel, fg_color=("#2A3A2A", "#1E2D1E"), border_width=1, border_color=("#4CAF50", "#2E7D32"), corner_radius=8)
        self.frame_vars.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 2))
        
        self.lbl_vars_header = ctk.CTkLabel(self.frame_vars, text="📋 Verfügbare Variablen", font=ctk.CTkFont(size=11, weight="bold"), text_color="#66BB6A")
        self.lbl_vars_header.pack(anchor="w", padx=10, pady=(4, 0))
        self.lbl_vars_content = ctk.CTkLabel(self.frame_vars, text="", font=ctk.CTkFont(size=11), text_color="#A5D6A7", wraplength=500, justify="left")
        self.lbl_vars_content.pack(anchor="w", padx=10, pady=(0, 4))

        # Sub-Actions Section
        self.frame_subs_container = ctk.CTkFrame(self.editor_panel, fg_color=("gray85", "#262626"), border_width=1, border_color=("gray75", "#333333"), corner_radius=10)
        self.frame_subs_container.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        self.editor_panel.grid_rowconfigure(3, weight=2) # Subactions get slightly more weight
        
        ctk.CTkLabel(self.frame_subs_container, text="Sub-Actions", font=ctk.CTkFont(weight="bold")).pack(side="top", anchor="w", padx=15, pady=(10, 0))

        subs_btn_frame = ctk.CTkFrame(self.frame_subs_container, fg_color="transparent")
        subs_btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        self.btn_add_sub = ctk.CTkButton(subs_btn_frame, text="+ Add Sub-Action", height=32, font=ctk.CTkFont(weight="bold"), fg_color="#10B981", hover_color="#059669", command=self.add_sub_dialog)
        self.btn_add_sub.pack(fill="x")

        self.scroll_subs = ctk.CTkScrollableFrame(self.frame_subs_container, fg_color="transparent")
        self.scroll_subs.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        # Save Button Main
        self.btn_save = ctk.CTkButton(self, text="Save Actions", fg_color="green", command=self.save_actions)
        self.btn_save.grid(row=1, column=0, columnspan=2, pady=10)

        # Bind scroll events to scroll frames, canvases, and inner frames so gaps/margins scroll smoothly
        for sc in [self.scroll_subs, self.scroll_triggers, self.action_listbox]:
            self._bind_scroll_events(sc)
            if hasattr(sc, '_parent_canvas'): self._bind_scroll_events(sc._parent_canvas)
            if hasattr(sc, '_parent_frame'): self._bind_scroll_events(sc._parent_frame)

        self.refresh_action_list()

    def on_header_change(self):
        if getattr(self, '_is_loading_action', False) or not self.current_action: return
        self.commit_current_changes()
        
        # Debounce/throttle the list refresh to avoid UI stutter if user types fast
        if hasattr(self, '_refresh_timer'):
            self.after_cancel(self._refresh_timer)
        self._refresh_timer = self.after(500, self._delayed_refresh_list_preserve_selection)
        
    def _delayed_refresh_list_preserve_selection(self):
        # We need to remember which action was selected
        if not self.current_action: return
        try:
            current_idx = self.actions.index(self.current_action)
            self.refresh_action_list()
            # Restore selection visuals without re-triggering load
            # Action list refresh re-creates all widgets, so we don't have a reliable "selection" 
            # state other than the loaded right panel. Just refreshing the list is enough.
        except ValueError:
            pass

    def load_actions(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.actions = yaml.safe_load(f).get('actions', [])
        else:
            self.actions = []

    def save_actions(self):
        # Update current action loaded in UI back to self.actions list
        self.commit_current_changes()
        
        data = {'actions': self.actions}
        with open(self.config_file, 'w') as f:
            yaml.dump(data, f)
        messagebox.showinfo("Saved", "Actions saved! (Reloading...)")
        self._send_reload_signal()

    def _send_reload_signal(self):
        def run():
            import asyncio
            import websockets
            import json
            async def send():
                try:
                    async with websockets.connect(get_ws_url()) as ws:
                        await ws.send(json.dumps({"event": "reload_actions"}))
                        print("Reload signal sent.")
                except Exception as e:
                    print(f"Reload Signal Failed: {e}")
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send())
                loop.close()
            except Exception as e:
                print(f"Reload Signal Error: {e}")

        import threading
        threading.Thread(target=run, daemon=True).start()

    def on_hot_switch_toggle(self):
        if not self.current_action: return
        
        # 1. Update local state
        new_state = self.var_enabled.get()
        self.current_action['enabled'] = new_state
        
        # 2. Send WS
        def run():
            import asyncio
            import websockets
            import json
            async def send():
                try:
                    async with websockets.connect(get_ws_url()) as ws:
                        payload = {
                            "event": "set_action_state", 
                            "data": {
                                "action": self.current_action.get('name'), 
                                "state": new_state
                            }
                        }
                        await ws.send(json.dumps(payload))
                except Exception as e:
                    print(f"HotSwitch Failed: {e}")
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send())
                loop.close()
            except Exception as e:
                print(f"HotSwitch Error: {e}")

        import threading
        threading.Thread(target=run, daemon=True).start()
        
        # 3. Update List UI (Delayed to allow thread start)
        # We don't want to loose selection, so we rely on the header switch state for visual feedback
        # But we should update the list text (Off) marker.
        # If we refresh, we lose selection.
        # Let's just refresh and select back? 
        # Easier: Don't refresh list instantly, let user save if they want permanent visual update in list?
        # User said "HotSwitch". Visual feedback in list is secondary to functionality.
        # But helpful.
        # I'll enable a lightweight refresh or just ignore list update for now to avoid UX jitter.
        # Actually, self.refresh_action_list() destroys widgets.
        # Let's skip list refresh for now to be smoother. The Switch itself shows the state.

    def refresh_action_list(self):
        self._action_item_buttons = {}
        for widget in self.action_listbox.winfo_children():
            widget.destroy()
            
        # Group actions
        grouped = {}
        for action in self.actions:
            g = action.get('group', 'General') or 'General'
            if g not in grouped: grouped[g] = []
            grouped[g].append(action)
            
        # Display Groups
        sorted_groups = sorted(grouped.keys())
        for gi, group_name in enumerate(sorted_groups):
            # Assign color from palette
            group_color = self._group_colors[gi % len(self._group_colors)]
            is_collapsed = group_name in self.collapsed_groups
            arrow = "▶" if is_collapsed else "▼"
            action_count = len(grouped[group_name])
            
            # Group Header Frame
            header_frame = ctk.CTkFrame(self.action_listbox, fg_color="transparent", height=28)
            header_frame.pack(fill="x", pady=(4, 1))
            header_frame.pack_propagate(False)
            
            # Color bar (compact)
            color_bar = ctk.CTkFrame(header_frame, width=3, fg_color=group_color, corner_radius=1)
            color_bar.pack(side="left", fill="y", padx=(0, 4))
            
            # Collapse button + Group name
            header_btn = ctk.CTkButton(
                header_frame, 
                text=f"{arrow} {group_name} ({action_count})",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="transparent", 
                text_color=group_color,
                hover_color=("gray85", "#2A2A2A"),
                height=24,
                anchor="w",
                command=lambda g=group_name: self.toggle_group(g)
            )
            header_btn.pack(side="left", fill="x", expand=True)
            
            # Rename button
            rename_btn = ctk.CTkButton(
                header_frame, text="✎", width=22, height=22,
                font=ctk.CTkFont(size=10),
                fg_color="transparent", text_color="gray60",
                hover_color=("gray80", "#333333"),
                command=lambda g=group_name: self.rename_group(g)
            )
            rename_btn.pack(side="right", padx=(0, 2))
            
            # Items (only if not collapsed)
            if not is_collapsed:
                for action in grouped[group_name]:
                    # Find original index
                    idx = self.actions.index(action)
                    
                    name_txt = action.get('name', 'Untitled')
                    if not action.get('enabled', True):
                        name_txt += " (Off)"
                    
                    # Highlight selected action
                    is_selected = (action is self.current_action)
                    btn_fg = group_color if is_selected else "transparent"
                    btn_border = group_color if is_selected else ("gray75", "#444444")
                        
                    btn = ctk.CTkButton(
                        self.action_listbox, text=name_txt, 
                        command=lambda i=idx: self.select_action(i),
                        fg_color=btn_fg, 
                        border_width=1, 
                        border_color=btn_border,
                        text_color=("gray10", "gray90"),
                        hover_color=("gray80", "#333333")
                    )
                    btn.pack(fill="x", pady=2, padx=(10, 0))
                    self._action_item_buttons[idx] = (btn, group_color)
                    self._bind_scroll_events(btn)
                
            self._bind_scroll_events(header_frame)

    def toggle_group(self, group_name):
        """Collapse or expand a group in the action list."""
        if group_name in self.collapsed_groups:
            self.collapsed_groups.discard(group_name)
        else:
            self.collapsed_groups.add(group_name)
        self._save_collapsed_groups()
        self.refresh_action_list()

    def _load_collapsed_groups(self):
        """Load collapsed group state from disk."""
        import json
        try:
            if os.path.exists('.group_state.json'):
                with open('.group_state.json', 'r') as f:
                    return set(json.load(f))
        except: pass
        return set()

    def _save_collapsed_groups(self):
        """Save collapsed group state to disk."""
        import json
        try:
            with open('.group_state.json', 'w') as f:
                json.dump(list(self.collapsed_groups), f)
        except: pass

    def rename_group(self, old_name):
        """Rename a group via dialog. Updates all actions in that group."""
        new_name = simpledialog.askstring("Gruppe umbenennen", f"Neuer Name für '{old_name}':", initialvalue=old_name)
        if not new_name or new_name == old_name:
            return
        # Update all actions in this group
        for action in self.actions:
            if (action.get('group', 'General') or 'General') == old_name:
                action['group'] = new_name
        # Update collapsed state
        if old_name in self.collapsed_groups:
            self.collapsed_groups.discard(old_name)
            self.collapsed_groups.add(new_name)
        # Update combo if current action was in this group
        if self.var_action_group.get() == old_name:
            self.var_action_group.set(new_name)
        self._update_group_combo()
        self.refresh_action_list()
        self.save_actions()

    def get_group_names(self):
        """Returns a sorted list of all unique group names currently in use."""
        groups = set()
        for action in self.actions:
            g = action.get('group', 'General') or 'General'
            groups.add(g)
        if not groups:
            groups.add('General')
        return sorted(groups)

    def _update_group_combo(self):
        """Refreshes the group ComboBox values with all existing group names."""
        groups = self.get_group_names()
        self.combo_group.configure(values=groups)

    def _update_context_vars(self, triggers):
        """Update the context variables info panel based on the action's triggers."""
        if not triggers:
            self.lbl_vars_content.configure(text="Keine Trigger konfiguriert")
            return
        
        # Collect all unique variables from all triggers
        all_vars = set()
        for t in triggers:
            t_type = t.get('type', '')
            vars_list = TRIGGER_CONTEXT_VARS.get(t_type, [])
            all_vars.update(vars_list)
        
        if all_vars:
            vars_text = "  ".join(sorted(all_vars))
            self.lbl_vars_content.configure(text=vars_text)
        else:
            self.lbl_vars_content.configure(text="Keine Variablen verfügbar")

    # --- SCROLL FIX (Universal hierarchy-traversal container mouse wheel routing) ---
    def _on_mouse_wheel(self, event):
        w = getattr(event, 'widget', None)
        if not w:
            return

        canvas = None
        curr = w
        while curr:
            if hasattr(curr, '_parent_canvas'):
                canvas = getattr(curr, '_parent_canvas', None)
                if canvas: break
            w_str = str(curr)
            if hasattr(self, 'scroll_subs'):
                sc_canvas = str(getattr(self.scroll_subs, '_parent_canvas', ''))
                if sc_canvas and sc_canvas in w_str:
                    canvas = self.scroll_subs._parent_canvas
                    break
            if hasattr(self, 'scroll_triggers'):
                st_canvas = str(getattr(self.scroll_triggers, '_parent_canvas', ''))
                if st_canvas and st_canvas in w_str:
                    canvas = self.scroll_triggers._parent_canvas
                    break
            if hasattr(self, 'action_listbox'):
                lb_canvas = str(getattr(self.action_listbox, '_parent_canvas', ''))
                if lb_canvas and lb_canvas in w_str:
                    canvas = self.action_listbox._parent_canvas
                    break
            curr = getattr(curr, 'master', None)

        if not canvas:
            return

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

    def _bind_scroll_events(self, widget):
        if not widget: return
        try:
            widget.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-4>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-5>", self._on_mouse_wheel, add="+")
        except Exception:
            pass

        canvas = getattr(widget, '_parent_canvas', None)
        if canvas:
            try:
                canvas.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
                canvas.bind("<Button-4>", self._on_mouse_wheel, add="+")
                canvas.bind("<Button-5>", self._on_mouse_wheel, add="+")
            except Exception:
                pass

        parent_frame = getattr(widget, '_parent_frame', None)
        if parent_frame:
            try:
                parent_frame.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
                parent_frame.bind("<Button-4>", self._on_mouse_wheel, add="+")
                parent_frame.bind("<Button-5>", self._on_mouse_wheel, add="+")
            except Exception:
                pass

        try:
            for child in widget.winfo_children():
                self._bind_scroll_events(child)
        except Exception:
            pass
    # --- SCROLL FIX END ---

    def _update_sidebar_button_selection(self, selected_index):
        """Updates visual selection state of sidebar buttons without destroying widgets (no flicker!)."""
        if not hasattr(self, '_action_item_buttons'):
            return
        selected_action = self.actions[selected_index] if 0 <= selected_index < len(self.actions) else None
        for idx, (btn, group_color) in self._action_item_buttons.items():
            if idx < len(self.actions) and self.actions[idx] is selected_action:
                btn.configure(fg_color=group_color, border_color=group_color)
            else:
                btn.configure(fg_color="transparent", border_color=("gray75", "#444444"))

    def select_action(self, index):
        self.commit_current_changes()
        self._is_loading_action = True
        self.current_action = self.actions[index]
        self.var_action_name.set(self.current_action.get('name', ''))
        self.var_action_group.set(self.current_action.get('group', 'General'))
        self.var_queue.set(self.current_action.get('queue', 'Default'))
        self.var_cooldown.set(str(self.current_action.get('cooldown', 0)))
        self.var_enabled.set(self.current_action.get('enabled', True))
        self._update_group_combo()
        
        # Smooth in-place selection update (Zero flickering!)
        self._update_sidebar_button_selection(index)
        
        self.refresh_details()
        self._is_loading_action = False

    def test_current_action(self):
        """Executes the currently selected action directly via ActionEngine or WS trigger."""
        if not hasattr(self, 'current_action') or not self.current_action:
            return
        act_name = self.current_action.get('name')
        if not act_name:
            return

        self.commit_current_changes()

        port = 8080
        cfg_file = os.path.join(BASE_DIR, "config.yaml")
        if os.path.exists(cfg_file):
            try:
                import yaml
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    if isinstance(cfg, dict) and "server" in cfg:
                        port = cfg["server"].get("port", 8080)
            except Exception:
                pass

        def _execute_or_send():
            sent = False
            try:
                import websockets, json, asyncio
                async def _send():
                    async with websockets.connect(f"ws://localhost:{port}", open_timeout=2) as ws:
                        await ws.send(json.dumps({"event": "trigger_action_by_name", "data": {"action": act_name}}))
                asyncio.run(_send())
                sent = True
                print(f"[ActionEditor] Sent WS trigger for '{act_name}' to port {port}")
            except Exception as e:
                print(f"[ActionEditor] WS trigger failed ({e}), falling back to direct ActionEngine execution.")

            if not sent:
                try:
                    import asyncio
                    from core.action_engine import ActionEngine
                    ae = ActionEngine(self.config_file)
                    asyncio.run(ae.execute_action(self.current_action, {}))
                    print(f"[ActionEditor] Executed action '{act_name}' directly via ActionEngine.")
                except Exception as ex:
                    print(f"[ActionEditor] Direct execution error: {ex}")

        import threading
        threading.Thread(target=_execute_or_send, daemon=True).start()

    def open_queue_manager(self):
        """Opens the Queue Manager & Live Monitor Dialog."""
        engine = getattr(self, 'action_engine', None)
        QueueManagerDialog(self, action_engine=engine)

    def commit_current_changes(self):
        if self.current_action:
            self.current_action['name'] = self.var_action_name.get()
            self.current_action['group'] = self.var_action_group.get()
            self.current_action['queue'] = self.var_queue.get() or 'Default'
            self.current_action['enabled'] = self.var_enabled.get()
            try:
                self.current_action['cooldown'] = int(self.var_cooldown.get() or 0)
            except:
                self.current_action['cooldown'] = 0
            # Triggers/Subs are modified directly in the list references usually, 
            # so strict commit might not be needed if references are kept.
            pass

    def add_action(self):
        # Let user pick a group from existing ones or type a new name
        groups = self.get_group_names()
        new_action = {'name': 'New Action', 'group': groups[0] if groups else 'General', 'enabled': True, 'triggers': [], 'sub_actions': []}
        self.actions.append(new_action)
        self.refresh_action_list()
        self.select_action(len(self.actions)-1)

    def delete_current_action(self):
        if not self.current_action: return
        if not messagebox.askyesno("Delete", "Delete this action?"): return
        
        self.actions.remove(self.current_action)
        self.current_action = None
        self.var_action_name.set("")
        self.var_action_group.set("")
        self.refresh_details()
        self.refresh_action_list()

    def refresh_details(self):
        # Clear
        for w in self.scroll_triggers.winfo_children(): w.destroy()
        for w in self.scroll_subs.winfo_children(): w.destroy()
        
        if not self.current_action:
            self._update_context_vars([])
            return
        
        self._update_context_vars(self.current_action.get('triggers', []))
        
        # Triggers
        triggers = self.current_action.get('triggers', [])
        for i, t in enumerate(triggers):
            f = ctk.CTkFrame(self.scroll_triggers, fg_color=("gray90", "#3A3A3A"), border_width=1, border_color=("gray80", "#4D4D4D"), corner_radius=6)
            f.pack(fill="x", pady=4, padx=5)
            text = TRIGGER_DISPLAY_NAMES.get(t['type'], t['type'])
            if 'command' in t: 
                perm = t.get('permission', 'Everyone')
                text += f": {t['command']} [{perm}]"
            elif 'scene_name' in t: text += f": {t['scene_name']}"
            elif 'min_viewers' in t: text += f" (>{t['min_viewers']})"
            elif 'interval' in t: text += f" ({t['interval']}s)"
            elif 'reward_title' in t: text += f": {t['reward_title']}"
            elif t['type'] in ['twitch_first_message', 'youtube_first_message'] and t.get('user'): text += f" (User: {t['user']})"
            elif t['type'] == 'twitch_watch_streak' and t.get('streak_value'): text += f" (={t['streak_value']})"
            
            lbl = ctk.CTkLabel(f, text=text)
            lbl.pack(side="left", padx=5)
            
            # Controls (Right side)
            btn_frame = ctk.CTkFrame(f, fg_color="transparent")
            btn_frame.pack(side="right", padx=5)

            # Move Up
            if i > 0:
                ctk.CTkButton(btn_frame, text="↑", width=24, fg_color="#6B7280", hover_color="#4B5563", command=lambda x=i: self.move_trigger_up(x)).pack(side="right", padx=2)
            else:
                 ctk.CTkLabel(btn_frame, text=" ", width=24).pack(side="right", padx=2) # Spacer
                 
            # Move Down
            if i < len(triggers) - 1:
                ctk.CTkButton(btn_frame, text="↓", width=24, fg_color="#6B7280", hover_color="#4B5563", command=lambda x=i: self.move_trigger_down(x)).pack(side="right", padx=2)
            else:
                 ctk.CTkLabel(btn_frame, text=" ", width=24).pack(side="right", padx=2) # Spacer

            # Edit btn
            ctk.CTkButton(btn_frame, text="✎", width=24, fg_color="#3B82F6", hover_color="#2563EB", command=lambda x=t: self.edit_trigger(x)).pack(side="right", padx=2)
            # Del btn
            ctk.CTkButton(btn_frame, text="X", width=24, fg_color="#EF4444", hover_color="#DC2626", command=lambda x=t: self.remove_trigger(x)).pack(side="right", padx=2)
            self._bind_scroll_events(f)

        # Sub Actions
        sub_actions = self.current_action.get('sub_actions', [])
        for i, s in enumerate(sub_actions):
            f = ctk.CTkFrame(self.scroll_subs, fg_color=("gray90", "#3A3A3A"), border_width=1, border_color=("gray80", "#4D4D4D"), corner_radius=6)
            f.pack(fill="x", pady=4, padx=5)
            
            summary = SUB_ACTION_DISPLAY_NAMES.get(s['type'], s['type'])
            if 'message' in s: summary += f": {s['message'][:20]}..."
            elif 'ms' in s: summary += f": {s['ms']}ms"
            elif 'folder' in s: summary += f": {s['folder']}"
            elif 'file' in s: summary += f": {os.path.basename(s['file'])}"
            elif 'action_name' in s: 
                if s['type'] == 'set_action_state':
                    summary += f": '{s['action_name']}' -> {s.get('state')} ({s.get('duration')}s)"
                else: 
                    summary += f": -> {s['action_name']}"
                    if s.get('var_name'):
                        summary += f" ({s['var_name']}={s.get('var_value')})"
            elif s['type'] == 'random_action_group':
                summary += f": {len(s.get('targets', []))} Actions"
            elif s['type'] in ['twitch_enable_reward', 'twitch_disable_reward']:
                summary += f": {s.get('reward_title', '')}"
            
            lbl = ctk.CTkLabel(f, text=summary)
            lbl.pack(side="left", padx=5)
            
            # Controls
            btn_frame = ctk.CTkFrame(f, fg_color="transparent")
            btn_frame.pack(side="right", padx=5)

            if i > 0:
                ctk.CTkButton(btn_frame, text="↑", width=24, fg_color="#6B7280", hover_color="#4B5563", command=lambda x=i: self.move_subaction_up(x)).pack(side="right", padx=2)
            else:
                 ctk.CTkLabel(btn_frame, text=" ", width=24).pack(side="right", padx=2)

            if i < len(sub_actions) - 1:
                ctk.CTkButton(btn_frame, text="↓", width=24, fg_color="#6B7280", hover_color="#4B5563", command=lambda x=i: self.move_subaction_down(x)).pack(side="right", padx=2)
            else:
                 ctk.CTkLabel(btn_frame, text=" ", width=24).pack(side="right", padx=2)

            ctk.CTkButton(btn_frame, text="✎", width=24, fg_color="#3B82F6", hover_color="#2563EB", command=lambda x=s: self.edit_sub_action(x)).pack(side="right", padx=2)
            ctk.CTkButton(btn_frame, text="X", width=24, fg_color="#EF4444", hover_color="#DC2626", command=lambda x=s: self.remove_sub(x)).pack(side="right", padx=2)
            self._bind_scroll_events(f)

    def remove_trigger(self, item):
        self.current_action['triggers'].remove(item)
        self.refresh_details()

    def remove_sub(self, item):
        self.current_action['sub_actions'].remove(item)
        self.refresh_details()

    def add_trigger_dialog(self):
        if not self.current_action: return
        
        dialog = TriggerDialog(self)
        self.wait_window(dialog)
        
        if dialog.result:
             self.current_action['triggers'].append(dialog.result)
             self.refresh_details()

    def add_sub_dialog(self):
        if not self.current_action: return
        # Mockup Selection
        # We need a proper Selector Dialog here
        dialog = SubActionDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.current_action['sub_actions'].append(dialog.result)
            self.refresh_details()

    def edit_trigger(self, trigger_data):
        # We need the index to replace it, or modify object in place if it's the same dict ref
        # dicts are mutable, but for safety lets replace content
        dialog = TriggerDialog(self, initial_data=trigger_data)
        self.wait_window(dialog)
        
        if dialog.result:
            trigger_data.clear()
            trigger_data.update(dialog.result)
            self.refresh_details()

    def edit_sub_action(self, sub_data):
        dialog = SubActionDialog(self, initial_data=sub_data)
        self.wait_window(dialog)
        if dialog.result:
            sub_data.clear()
            sub_data.update(dialog.result)
            self.refresh_details()

    def move_trigger_up(self, index):
        if index > 0:
            self.current_action['triggers'].insert(index-1, self.current_action['triggers'].pop(index))
            self.refresh_details()

    def move_trigger_down(self, index):
        if index < len(self.current_action['triggers']) - 1:
            self.current_action['triggers'].insert(index+1, self.current_action['triggers'].pop(index))
            self.refresh_details()

    def move_subaction_up(self, index):
        if index > 0:
            self.current_action['sub_actions'].insert(index-1, self.current_action['sub_actions'].pop(index))
            self.refresh_details()

    def move_subaction_down(self, index):
         if index < len(self.current_action['sub_actions']) - 1:
            self.current_action['sub_actions'].insert(index+1, self.current_action['sub_actions'].pop(index))
            self.refresh_details()

class SubActionDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_data=None):
        super().__init__(parent)
        self.title("Edit Sub-Action" if initial_data else "Add Sub-Action")
        self.geometry("450x600")
        self.result = None
        self.initial_data = initial_data or {}
        
        # --- TYPE ---
        ctk.CTkLabel(self, text="Action Type:").pack(pady=5)
        # Use initial type or default
        start_type = self.initial_data.get('type', "twitch_chat")
        
        # Display name mappings for sub-action types
        self.sa_display_to_internal = {v: k for k, v in SUB_ACTION_DISPLAY_NAMES.items()}
        self.sa_internal_to_display = SUB_ACTION_DISPLAY_NAMES.copy()
        
        start_display = self.sa_internal_to_display.get(start_type, start_type)
        self.type_var = ctk.StringVar(value=start_display)
        
        display_names = sorted(self.sa_internal_to_display.values())
        
        self.combo = ctk.CTkComboBox(self, variable=self.type_var, 
                                     values=display_names,
                                     command=lambda choice: self.on_type_change(
                                         self.sa_display_to_internal.get(choice, choice)))
        self.combo.pack(pady=5)
        
        # --- DYNAMIC FRAME ---
        self.frame_config = ctk.CTkScrollableFrame(self)
        self.frame_config.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Holders for widgets
        self.widgets = {}
        
        # --- PROBABILITY (Common for all) ---
        self.frame_prob = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_prob.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(self.frame_prob, text="Probability:").pack(side="left")
        
        self.lbl_prob = ctk.CTkLabel(self.frame_prob, text="100%", width=40)
        self.lbl_prob.pack(side="right")
        
        def update_prob(val):
            self.lbl_prob.configure(text=f"{int(val)}%")
            
        init_prob = float(self.initial_data.get('probability', 1.0)) * 100
        self.prob_slider = ctk.CTkSlider(self.frame_prob, from_=0, to=100, number_of_steps=100, command=update_prob)
        self.prob_slider.set(init_prob)
        self.prob_slider.pack(fill="x", padx=5)
        update_prob(init_prob) # Set initial label
        
        # OK Button
        ctk.CTkButton(self, text="Save" if initial_data else "Add", command=self.on_ok).pack(pady=10)
        
        self.on_type_change(start_type)

    def on_type_change(self, choice):
        # Clear old widgets
        for w in self.frame_config.winfo_children(): w.destroy()
        self.widgets = {}
        
        # Helper to set value if editing and types match
        def get_val(key, default=""):
            if self.initial_data and self.initial_data.get('type') == choice:
                 return str(self.initial_data.get(key, default))
            return default

        # Helper for Device Dropdown
        def add_device_selector():
            ctk.CTkLabel(self.frame_config, text="Audio Device:").pack(anchor="w")
            
            # Get Devices
            try:
                if not pygame.get_init(): pygame.init()
                devices = ['Default'] + sdl_audio.get_audio_device_names(False)
            except:
                devices = ['Default']
                
            dev_var = ctk.StringVar(value=get_val('device', 'Default'))
            combo = ctk.CTkComboBox(self.frame_config, variable=dev_var, values=devices)
            combo.pack(fill="x", pady=5)
            self.widgets['device'] = dev_var

        if choice == "twitch_chat":
            ctk.CTkLabel(self.frame_config, text="Chat Message:").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('message'))
            entry.pack(fill="x", pady=5)
            self.widgets['message'] = entry
            
        elif choice == "youtube_chat":
            ctk.CTkLabel(self.frame_config, text="YouTube Chat Message:").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('message'))
            entry.pack(fill="x", pady=5)
            self.widgets['message'] = entry
            
        elif choice == "twitch_command":
            ctk.CTkLabel(self.frame_config, text="Command:").pack(anchor="w")
            cmd_var = ctk.StringVar(value=get_val('command', 'Announce'))
            cmd_combo = ctk.CTkComboBox(self.frame_config, variable=cmd_var, values=["Announce", "Shoutout", "Ban", "Timeout", "VIP", "Un-VIP", "Commercial"])
            cmd_combo.pack(fill="x", pady=5)
            self.widgets['command'] = cmd_var
            
            ctk.CTkLabel(self.frame_config, text="Target User (e.g. %user%):").pack(anchor="w")
            target_entry = ctk.CTkEntry(self.frame_config)
            target_entry.insert(0, get_val('target'))
            target_entry.pack(fill="x", pady=5)
            self.widgets['target'] = target_entry
            
            ctk.CTkLabel(self.frame_config, text="Message / Reason / Duration:").pack(anchor="w")
            msg_entry = ctk.CTkEntry(self.frame_config)
            msg_entry.insert(0, get_val('message'))
            msg_entry.pack(fill="x", pady=5)
            self.widgets['message'] = msg_entry
            
        elif choice == "log":
             ctk.CTkLabel(self.frame_config, text="Log Message:").pack(anchor="w")
             entry = ctk.CTkEntry(self.frame_config)
             entry.insert(0, get_val('message'))
             entry.pack(fill="x", pady=5)
             self.widgets['message'] = entry
             
        elif choice == "delay":
            ctk.CTkLabel(self.frame_config, text="Term (ms):").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('ms', '1000'))
            entry.pack(fill="x", pady=5)
            self.widgets['ms'] = entry

        elif choice == "play_sound":
            ctk.CTkLabel(self.frame_config, text="Sound File:").pack(anchor="w")
            f_frame = ctk.CTkFrame(self.frame_config, fg_color="transparent")
            f_frame.pack(fill="x")
            
            entry = ctk.CTkEntry(f_frame)
            entry.insert(0, get_val('file'))
            entry.pack(side="left", fill="x", expand=True)
            self.widgets['file'] = entry
            
            btn = ctk.CTkButton(f_frame, text="...", width=30, command=lambda: self.browse_file(entry))
            btn.pack(side="right", padx=5)
            
            add_device_selector()
            
            ctk.CTkLabel(self.frame_config, text="Volume (0-100%):").pack(anchor="w", pady=(10,0))
            
            def update_vol_lbl(val):
                lbl_vol.configure(text=f"{int(val)}%")
                
            init_vol = float(get_val('volume', '100'))
            
            slider = ctk.CTkSlider(self.frame_config, from_=0, to=100, number_of_steps=100, command=update_vol_lbl)
            slider.set(init_vol)
            slider.pack(fill="x", pady=5)
            self.widgets['volume_slider'] = slider
            
            lbl_vol = ctk.CTkLabel(self.frame_config, text=f"{int(init_vol)}%")
            lbl_vol.pack(anchor="n")

        elif choice == "playlist":
            ctk.CTkLabel(self.frame_config, text="Music Folder:").pack(anchor="w")
            f_frame = ctk.CTkFrame(self.frame_config, fg_color="transparent")
            f_frame.pack(fill="x")
            
            entry = ctk.CTkEntry(f_frame)
            entry.insert(0, get_val('folder'))
            entry.pack(side="left", fill="x", expand=True)
            self.widgets['folder'] = entry
            
            btn = ctk.CTkButton(f_frame, text="...", width=30, command=lambda: self.browse_folder(entry))
            btn.pack(side="right", padx=5)
            
            add_device_selector()
            
            # Volume Slider for Playlist
            ctk.CTkLabel(self.frame_config, text="Volume (0-100%):").pack(anchor="w", pady=(10,0))
            
            def update_vol_lbl(val):
                lbl_vol.configure(text=f"{int(val)}%")
                
            init_vol = float(get_val('volume', '100'))
            
            slider = ctk.CTkSlider(self.frame_config, from_=0, to=100, number_of_steps=100, command=update_vol_lbl)
            slider.set(init_vol)
            slider.pack(fill="x", pady=5)
            self.widgets['volume_slider'] = slider
            
            lbl_vol = ctk.CTkLabel(self.frame_config, text=f"{int(init_vol)}%")
            lbl_vol.pack(anchor="n")

        elif choice == "obs_set_scene":
            ctk.CTkLabel(self.frame_config, text="Scene Name:").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('scene'))
            entry.pack(fill="x", pady=5)
            self.widgets['scene'] = entry
            
        elif choice == "youtube_random_short":
             ctk.CTkLabel(self.frame_config, text="No configuration needed.\nMake sure to 'Sync Shorts' in 'Accounts' tab!").pack(pady=10)

        elif choice == "trigger_action":
            ctk.CTkLabel(self.frame_config, text="Auszulösende Action:").pack(anchor="w")
            
            # Get Action Names
            action_names = sorted([a.get('name', 'Untitled') for a in self.master.actions])
            
            act_var = ctk.StringVar(value=get_val('action_name'))
            combo = ctk.CTkComboBox(self.frame_config, variable=act_var, values=action_names)
            combo.pack(fill="x", pady=5)
            self.widgets['action_name'] = act_var

            # Custom variable configuration
            ctk.CTkLabel(self.frame_config, text="Variable weitergeben (Optional):", font=("", 12, "bold")).pack(anchor="w", pady=(15, 5))
            
            ctk.CTkLabel(self.frame_config, text="Name der Variable in Ziel-Action:").pack(anchor="w")
            var_name_entry = ctk.CTkEntry(self.frame_config, placeholder_text="z.B. ziel_user")
            var_name_entry.insert(0, get_val('var_name'))
            var_name_entry.pack(fill="x", pady=5)
            self.widgets['var_name'] = var_name_entry

            ctk.CTkLabel(self.frame_config, text="Wert / Quelle:").pack(anchor="w")
            
            options = [
                "Keine", 
                "%user% (Auslösender Benutzer)", 
                "%message% (Chatnachricht)", 
                "%game% (Aktuelles Spiel)", 
                "%input% (Kanalpunkte Eingabe)", 
                "Eigener Wert..."
            ]
            
            initial_val = get_val('var_value')
            if not initial_val:
                start_opt = "Keine"
            elif initial_val == "%user%":
                start_opt = "%user% (Auslösender Benutzer)"
            elif initial_val == "%message%":
                start_opt = "%message% (Chatnachricht)"
            elif initial_val == "%game%":
                start_opt = "%game% (Aktuelles Spiel)"
            elif initial_val == "%input%":
                start_opt = "%input% (Kanalpunkte Eingabe)"
            else:
                start_opt = "Eigener Wert..."
                
            opt_var = ctk.StringVar(value=start_opt)
            
            custom_val_frame = ctk.CTkFrame(self.frame_config, fg_color="transparent")
            custom_val_entry = ctk.CTkEntry(custom_val_frame, placeholder_text="Eigener Wert oder Text...")
            
            if start_opt == "Eigener Wert...":
                custom_val_entry.insert(0, initial_val)
                custom_val_frame.pack(fill="x", pady=5)
                
            def on_opt_change(selected_opt):
                if selected_opt == "Eigener Wert...":
                    custom_val_frame.pack(fill="x", pady=5)
                else:
                    custom_val_frame.pack_forget()
                    
            opt_combo = ctk.CTkComboBox(self.frame_config, variable=opt_var, values=options, command=on_opt_change)
            opt_combo.pack(fill="x", pady=5)
            custom_val_entry.pack(fill="x")
            
            self.widgets['var_option'] = opt_var
            self.widgets['custom_var_value'] = custom_val_entry

        elif choice == "set_action_state":
            ctk.CTkLabel(self.frame_config, text="Target Action Name:").pack(anchor="w")
            
            # Get Action Names
            action_names = sorted([a.get('name', 'Untitled') for a in self.master.actions])
            
            act_var = ctk.StringVar(value=get_val('action_name'))
            combo = ctk.CTkComboBox(self.frame_config, variable=act_var, values=action_names)
            combo.pack(fill="x", pady=5)
            self.widgets['action_name'] = act_var
            
            ctk.CTkLabel(self.frame_config, text="New State:").pack(anchor="w")
            state_var = ctk.StringVar(value=get_val('state', 'toggle'))
            ctk.CTkComboBox(self.frame_config, variable=state_var, values=['on', 'off', 'toggle']).pack(fill="x", pady=5)
            self.widgets['state'] = state_var
            
            ctk.CTkLabel(self.frame_config, text="Duration (seconds, 0=permanent):").pack(anchor="w")
            dur_entry = ctk.CTkEntry(self.frame_config)
            dur_entry.insert(0, get_val('duration', '0'))
            dur_entry.pack(fill="x", pady=5)
            self.widgets['duration'] = dur_entry

        elif choice == "set_volume":
            # Target
            ctk.CTkLabel(self.frame_config, text="Target:").pack(anchor="w")
            t_var = ctk.StringVar(value=get_val('target', 'sfx'))
            ctk.CTkComboBox(self.frame_config, variable=t_var, values=['sfx', 'playlist']).pack(fill="x", pady=5)
            self.widgets['target'] = t_var
            
            # Mode
            ctk.CTkLabel(self.frame_config, text="Mode:").pack(anchor="w")
            m_var = ctk.StringVar(value=get_val('mode', 'set'))
            ctk.CTkComboBox(self.frame_config, variable=m_var, values=['set', 'adjust']).pack(fill="x", pady=5)
            self.widgets['mode'] = m_var
            
            # Value
            ctk.CTkLabel(self.frame_config, text="Value (0-100%):").pack(anchor="w")
            
            # Slider Logic
            def update_val_lbl(val):
                lbl_val.configure(text=f"{int(val)}%")
                
            init_val = float(get_val('value', '0.5'))
            # Check if stored as 0-1 or 0-100
            if init_val <= 1.0: init_val *= 100
            
            slider = ctk.CTkSlider(self.frame_config, from_=0, to=100, number_of_steps=100, command=update_val_lbl)
            slider.set(init_val)
            slider.pack(fill="x", pady=5)
            self.widgets['value_slider'] = slider # Special key
            
            lbl_val = ctk.CTkLabel(self.frame_config, text=f"{int(init_val)}%")
            lbl_val.pack(anchor="n")

        elif choice == "elevenlabs_tts":
            ctk.CTkLabel(self.frame_config, text="Text (+ Variables):").pack(anchor="w")
            entry = ctk.CTkEntry(self.frame_config)
            entry.insert(0, get_val('text'))
            entry.pack(fill="x", pady=5)
            self.widgets['text'] = entry

            ctk.CTkLabel(self.frame_config, text="Voice ID:").pack(anchor="w")
            v_entry = ctk.CTkEntry(self.frame_config)
            v_entry.insert(0, get_val('voice_id'))
            v_entry.pack(fill="x", pady=5)
            self.widgets['voice_id'] = v_entry
            
            add_device_selector()
            
            ctk.CTkLabel(self.frame_config, text="Volume (0-100%):").pack(anchor="w", pady=(10,0))
            def update_vol_lbl(val): lbl_vol.configure(text=f"{int(val)}%")
            init_vol = float(get_val('volume', '100'))
            slider = ctk.CTkSlider(self.frame_config, from_=0, to=100, number_of_steps=100, command=update_vol_lbl)
            slider.set(init_vol)
            slider.pack(fill="x", pady=5)
            self.widgets['volume_slider'] = slider
            lbl_vol = ctk.CTkLabel(self.frame_config, text=f"{int(init_vol)}%")
            lbl_vol.pack(anchor="n")

        elif choice == "twitch_create_clip":
             ctk.CTkLabel(self.frame_config, text="Post Clip link to Chat?").pack(anchor="w")
             # Default True
             post_var = ctk.BooleanVar(value=True)
             if self.initial_data and choice == self.initial_data.get('type'):
                  post_var.set(self.initial_data.get('post_to_chat', True))
                  
             chk = ctk.CTkCheckBox(self.frame_config, text="Yes", variable=post_var)
             chk.pack(pady=5)
             self.widgets['post_to_chat'] = post_var

        elif choice in ["twitch_enable_reward", "twitch_disable_reward"]:
            ctk.CTkLabel(self.frame_config, text="Twitch Reward auswählen:").pack(anchor="w")
            
            # Load rewards
            import json
            rewards_titles = []
            if os.path.exists("available_rewards.json"):
                try:
                    with open("available_rewards.json", "r", encoding="utf-8") as f:
                        rewards_data = json.load(f)
                        rewards_titles = [r.get('title') for r in rewards_data if r.get('title')]
                except Exception as e:
                    print(f"Failed to load rewards for subaction dropdown: {e}")
            
            if not rewards_titles:
                rewards_titles = ["Keine Rewards gefunden. Bitte aktualisieren in 'Twitch Rewards'."]
                
            rewards_titles = sorted(rewards_titles)
            
            reward_var = ctk.StringVar(value=get_val('reward_title', rewards_titles[0] if rewards_titles else ""))
            combo = ctk.CTkComboBox(self.frame_config, variable=reward_var, values=rewards_titles)
            combo.pack(fill="x", pady=5)
            self.widgets['reward_title'] = reward_var

        elif choice == "execute_csharp":
             # Container for Mode Selection
             ctk.CTkLabel(self.frame_config, text="Execution Mode:").pack(anchor="w")
             
             # Default to "File" if not set
             current_mode = get_val('csharp_mode', 'File')
             mode_var = ctk.StringVar(value=current_mode)
             self.widgets['csharp_mode'] = mode_var
             
             def toggle_mode(value):
                 mode_var.set(value)
                 if value == "File":
                     frame_file.pack(fill="x", pady=5)
                     frame_code.pack_forget()
                 else:
                     frame_file.pack_forget()
                     frame_code.pack(fill="both", expand=True, pady=5)
                     
             seg = ctk.CTkSegmentedButton(self.frame_config, values=["File", "Code"], command=toggle_mode)
             seg.set(current_mode)
             seg.pack(fill="x", pady=5)
             
             # --- FILE MODE ---
             frame_file = ctk.CTkFrame(self.frame_config, fg_color="transparent")
             
             ctk.CTkLabel(frame_file, text="C# Source File (.cs / .csx / .csproj / .exe):").pack(anchor="w")
             f_inner = ctk.CTkFrame(frame_file, fg_color="transparent")
             f_inner.pack(fill="x")
             
             entry_path = ctk.CTkEntry(f_inner)
             entry_path.insert(0, get_val('path'))
             entry_path.pack(side="left", fill="x", expand=True)
             self.widgets['path'] = entry_path
             
             btn = ctk.CTkButton(f_inner, text="...", width=30, command=lambda: self.browse_csharp(entry_path))
             btn.pack(side="right", padx=5)
             
             # --- CODE MODE ---
             frame_code = ctk.CTkFrame(self.frame_config, fg_color="transparent")
             
             ctk.CTkLabel(frame_code, text="Direct C# Script (Body of .csx):").pack(anchor="w")
             txt_code = ctk.CTkTextbox(frame_code, height=400, font=("Consolas", 12))
             txt_code.insert("0.0", get_val('code', 'Console.WriteLine("Hello from C#");'))
             txt_code.pack(fill="both", expand=True)
             self.widgets['code'] = txt_code
             
             # --- SHARED ARGS ---
             ctk.CTkLabel(self.frame_config, text="Arguments (Optional):").pack(anchor="w", pady=(10,0))
             entry_args = ctk.CTkEntry(self.frame_config)
             entry_args.insert(0, get_val('args'))
             entry_args.pack(fill="x", pady=5)
             self.widgets['args'] = entry_args
             
             # Initial Visibility
             if current_mode == "File":
                 frame_file.pack(fill="x", pady=5)
                 frame_code.pack_forget()
             else:
                 frame_file.pack_forget()
                 frame_code.pack(fill="both", expand=True, pady=5)

        elif choice == "random_action_group":
             ctk.CTkLabel(self.frame_config, text="Zufällige Sub-Aktionen (Summe muss 100% ergeben):").pack(anchor="w", pady=5)
             
             self.widgets['targets'] = []
             list_frame = ctk.CTkFrame(self.frame_config)
             list_frame.pack(fill="both", expand=True, pady=5)
             
             label_total = ctk.CTkLabel(self.frame_config, text="Total: 0%")
             label_total.pack(anchor="w")

             def update_total(*args):
                 total = 0
                 for _, sub_data, w_var in self.widgets['targets']:
                     try: total += float(w_var.get() or 0)
                     except: pass
                 label_total.configure(text=f"Total: {total:g}%")
                 if total != 100: label_total.configure(text_color="red")
                 else: label_total.configure(text_color=("black", "white"))

             def add_row(sub_data=None, weight=0):
                 if sub_data is None:
                     sub_data = {'type': 'twitch_chat'} # Default empty action
                     
                 row = ctk.CTkFrame(list_frame)
                 row.pack(fill="x", pady=2)
                 
                 # Display name for subaction
                 def get_display(d):
                     return d.get('type', 'Unknown')
                     
                 lbl_name = ctk.CTkLabel(row, text=get_display(sub_data), width=150, anchor="w")
                 lbl_name.pack(side="left", padx=5)
                 
                 # Edit Button to configure nested SubAction
                 def edit_nested():
                     # self.master is ActionEditorFrame in this context
                     # Create a nested dialog
                     dialog = SubActionDialog(self.master, initial_data=sub_data)
                     # SubActionDialog waits for window close
                     self.wait_window(dialog)
                     if dialog.result:
                         sub_data.clear()
                         sub_data.update(dialog.result)
                         lbl_name.configure(text=get_display(sub_data))
                 
                 ctk.CTkButton(row, text="Bearbeiten", width=80, command=edit_nested).pack(side="left", padx=5)
                 
                 w_var = ctk.StringVar(value=str(weight))
                 w_var.trace_add("write", update_total)
                 ctk.CTkEntry(row, textvariable=w_var, width=50).pack(side="left", padx=5)
                 ctk.CTkLabel(row, text="%").pack(side="left")
                 
                 def del_row():
                     row.destroy()
                     self.widgets['targets'] = [t for t in self.widgets['targets'] if t[0] != row]
                     update_total()
                     
                 ctk.CTkButton(row, text="X", width=30, fg_color="red", command=del_row).pack(side="right", padx=5)
                 self.widgets['targets'].append((row, sub_data, w_var))
                 update_total()
                 
             init_targets = self.initial_data.get('targets', []) if self.initial_data and self.initial_data.get('type') == choice else []
             if not init_targets: add_row(None, 100)
             else:
                 for t in init_targets: add_row(t.get('action', {}), t.get('weight', 0))
                 
             ctk.CTkButton(self.frame_config, text="+ Sub-Aktion hinzufügen", command=add_row).pack(pady=5)

        self._bind_scroll_events(self.frame_config)
        if hasattr(self.frame_config, '_parent_canvas'):
            self._bind_scroll_events(self.frame_config._parent_canvas)
        if hasattr(self.frame_config, '_parent_frame'):
            self._bind_scroll_events(self.frame_config._parent_frame)

    def _on_mouse_wheel(self, event):
        units = 0
        if hasattr(event, 'num') and event.num == 4:
            units = -1
        elif hasattr(event, 'num') and event.num == 5:
            units = 1
        elif hasattr(event, 'delta') and event.delta:
            units = int(-1 * (event.delta / 120))
            if units == 0:
                units = -1 if event.delta > 0 else 1

        if units != 0 and hasattr(self, 'frame_config') and hasattr(self.frame_config, '_parent_canvas'):
            try:
                self.frame_config._parent_canvas.yview_scroll(units, "units")
            except Exception:
                pass

    def _bind_scroll_events(self, widget):
        if not widget: return
        try:
            widget.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-4>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-5>", self._on_mouse_wheel, add="+")
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._bind_scroll_events(child)
        except Exception:
            pass

    def browse_folder(self, entry_widget):
        folder = filedialog.askdirectory()
        if folder:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, folder)

    def browse_file(self, entry_widget):
        filename = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.wav *.ogg")])
        if filename:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, filename)

    def browse_csharp(self, entry_widget):
        filename = filedialog.askopenfilename(filetypes=[("C# Source", "*.cs *.csx *.csproj"), ("Executable", "*.exe"), ("All", "*.*")])
        if filename:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, filename)

    def on_ok(self):
        display = self.type_var.get()
        t = self.sa_display_to_internal.get(display, display) if hasattr(self, 'sa_display_to_internal') else display
        res = {'type': t}
        
        # Harvest data
        try:
            if 'message' in self.widgets:
                res['message'] = self.widgets['message'].get()
            if 'text' in self.widgets:
                res['text'] = self.widgets['text'].get()
            if 'command' in self.widgets:
                res['command'] = self.widgets['command'].get()
            if 'voice_id' in self.widgets:
                res['voice_id'] = self.widgets['voice_id'].get()
            if 'ms' in self.widgets:
                 res['ms'] = int(self.widgets['ms'].get())
            if 'file' in self.widgets:
                res['file'] = self.widgets['file'].get()
            if 'folder' in self.widgets:
                res['folder'] = self.widgets['folder'].get()
            if 'device' in self.widgets:
                res['device'] = self.widgets['device'].get()
            if 'scene' in self.widgets:
                res['scene'] = self.widgets['scene'].get()
            if 'action_name' in self.widgets:
                res['action_name'] = self.widgets['action_name'].get()
            if 'target' in self.widgets:
                res['target'] = self.widgets['target'].get()
            if 'reward_title' in self.widgets:
                res['reward_title'] = self.widgets['reward_title'].get()
            if 'mode' in self.widgets:
                res['mode'] = self.widgets['mode'].get()
            if 'state' in self.widgets:
                res['state'] = self.widgets['state'].get()
            if 'duration' in self.widgets:
                 res['duration'] = int(self.widgets['duration'].get())
            if 'csharp_mode' in self.widgets:
                 res['csharp_mode'] = self.widgets['csharp_mode'].get()
            if 'code' in self.widgets:
                 res['code'] = self.widgets['code'].get("0.0", "end-1c")

            if 'path' in self.widgets:
                 res['path'] = self.widgets['path'].get()
            if 'args' in self.widgets:
                 res['args'] = self.widgets['args'].get()
            if 'post_to_chat' in self.widgets:
                 res['post_to_chat'] = self.widgets['post_to_chat'].get()
                
            if 'value_slider' in self.widgets:
                # Convert 0-100 slider to 0.0-1.0 for backend
                val = self.widgets['value_slider'].get()
                res['value'] = f"{val/100:.2f}"
            elif 'value' in self.widgets: # Fallback if widget name mismatch
                res['value'] = self.widgets['value'].get()
                
            if 'volume_slider' in self.widgets:
                # Keep 0-100 for play_sound config
                res['volume'] = str(int(self.widgets['volume_slider'].get()))
            elif 'volume' in self.widgets:
                res['volume'] = self.widgets['volume'].get()
                
            if 'targets' in self.widgets and t == 'random_action_group':
                 total = 0
                 targets = []
                 for _, sub_data, w_var in self.widgets['targets']:
                     w = float(w_var.get() or 0)
                     total += w
                     # Speichere die verschachtelte Sub-Action anstatt einen Namen
                     targets.append({'action': sub_data, 'weight': w})
                 if round(total, 2) != 100.0:
                     messagebox.showerror("Error", f"Die Summe der Wahrscheinlichkeiten muss 100% ergeben! (Aktuell: {total}%)")
                     return
                 res['targets'] = targets
                 
            # Probability
            if hasattr(self, 'prob_slider'):
                 prob = float(self.prob_slider.get()) / 100.0
                 res['probability'] = f"{prob:.2f}"

            if 'var_name' in self.widgets:
                res['var_name'] = self.widgets['var_name'].get().strip()
                
            if 'var_option' in self.widgets:
                opt = self.widgets['var_option'].get()
                if opt == "Keine":
                    res['var_value'] = ""
                elif opt.startswith("%user%"):
                    res['var_value'] = "%user%"
                elif opt.startswith("%message%"):
                    res['var_value'] = "%message%"
                elif opt.startswith("%game%"):
                    res['var_value'] = "%game%"
                elif opt.startswith("%input%"):
                    res['var_value'] = "%input%"
                elif opt == "Eigener Wert...":
                    res['var_value'] = self.widgets['custom_var_value'].get()
                
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric value!")
            return

        self.result = res
        self.destroy()

class TriggerDialog(ctk.CTkToplevel):
    def __init__(self, parent, initial_data=None):
        super().__init__(parent)
        self.title("Edit Trigger" if initial_data else "Add Trigger")
        self.geometry("400x450")
        self.result = None
        self.initial_data = initial_data or {}
        
        # Get initial type from data
        start_type = self.initial_data.get('type', "twitch_command")
        
        # Create friendly display names mapping
        trigger_types = [
            (k, v) for k, v in TRIGGER_DISPLAY_NAMES.items()
        ]
        
        self.type_mapping = {display: internal for internal, display in trigger_types}
        self.reverse_mapping = {internal: display for internal, display in trigger_types}
        
        # Find display name for initial type
        start_display = self.reverse_mapping.get(start_type, trigger_types[0][1])
        
        self.type_var = ctk.StringVar(value=start_display)
        self.combo = ctk.CTkComboBox(self, variable=self.type_var, 
                                     values=[display for _, display in trigger_types],
                                     command=self.on_type_change)
        self.combo.pack(pady=5)
        
        # --- DYNAMIC CONFIG FRAME ---
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- PERMISSION (Conditional) ---
        self.frame_perm = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_perm, text="Permission:").pack(anchor="w")
        self.perm_var = ctk.StringVar(value="Everyone")
        self.perm_combo = ctk.CTkComboBox(self.frame_perm, variable=self.perm_var, 
                                          values=["Everyone", "Subscriber", "VIP", "Moderator", "Broadcaster"])
        self.perm_combo.pack(fill="x", pady=5)

        # --- IGNORE SHARED CHAT (Conditional) ---
        self.frame_shared_chat = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.ignore_shared_var = ctk.BooleanVar(value=False)
        self.chk_ignore_shared = ctk.CTkCheckBox(self.frame_shared_chat, text="Gemeinsamen Chat ignorieren", variable=self.ignore_shared_var)
        self.chk_ignore_shared.pack(anchor="w", pady=5)
        
        self.entry_var = ctk.StringVar()
        self.lbl_config = ctk.CTkLabel(self.config_frame, text="Command (!cmd):")
        self.lbl_config.pack()
        
        self.entry_config = ctk.CTkEntry(self.config_frame, textvariable=self.entry_var)
        self.entry_config.pack(fill="x", padx=10, pady=5)
        
        # --- BLACKLIST ---
        self.frame_blacklist = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        ctk.CTkLabel(self.frame_blacklist, text="Ignorierte Benutzer (Blacklist, Komma-getrennt):").pack(anchor="w")
        self.blacklist_var = ctk.StringVar(value=self.initial_data.get('blacklist_users', ''))
        self.entry_blacklist = ctk.CTkEntry(self.frame_blacklist, textvariable=self.blacklist_var)
        self.entry_blacklist.pack(fill="x", pady=5)
        self.frame_blacklist.pack(fill="x", padx=10, pady=5)
        
        # OK BUTTON
        ctk.CTkButton(self, text="Save" if initial_data else "Add", command=self.on_ok).pack(pady=10)
        
        self.on_type_change(start_display)

    def on_type_change(self, choice):
        self.entry_var.set("") # Clear input default
        self.entry_config.pack(fill="x", padx=10, pady=5) # Ensure entry is visible by default
        
        # Map display name back to internal type
        internal_type = self.type_mapping.get(choice, "twitch_command")

        if hasattr(self, 'frame_perm'): self.frame_perm.pack_forget()
        if hasattr(self, 'frame_shared_chat'): self.frame_shared_chat.pack_forget()
        
        # But if editing, restore value
        val = ""
        if self.initial_data and self.initial_data.get('type') == internal_type:
             if internal_type == "twitch_command": 
                  val = self.initial_data.get('command', '')
                  self.perm_var.set(self.initial_data.get('permission', 'Everyone'))
                  self.ignore_shared_var.set(self.initial_data.get('ignore_shared_chat', False))
             elif internal_type == "youtube_command": val = self.initial_data.get('command', '')
             elif internal_type == "twitch_raid": val = str(self.initial_data.get('min_viewers', 0))
             elif internal_type == "timer": val = str(self.initial_data.get('interval', 60))
             elif internal_type == "obs_scene": val = self.initial_data.get('scene_name', '')
             elif internal_type == "twitch_redemption": val = self.initial_data.get('reward_title', '')
             elif internal_type in ["twitch_first_message", "youtube_first_message"]: val = self.initial_data.get('user', '')
             elif internal_type == "twitch_watch_streak": val = str(self.initial_data.get('streak_value', '0'))
             elif internal_type == "youtube_member_milestone": val = str(self.initial_data.get('min_months', 0))
             elif internal_type == "youtube_super_chat": val = str(self.initial_data.get('min_amount', 0))
             
        self.entry_var.set(val)

        if internal_type == "twitch_command":
            self.lbl_config.configure(text="Befehlsname (z.B. !start):")
            self.entry_config.configure(state="normal")
            self.frame_perm.pack(fill="x", pady=5)
            self.frame_shared_chat.pack(fill="x", pady=5)
        elif internal_type == "youtube_command":
            self.lbl_config.configure(text="Befehlsname (z.B. !start):")
            self.entry_config.configure(state="normal")
            self.frame_perm.pack_forget()
        elif internal_type == "twitch_raid":
            self.lbl_config.configure(text="Min. Zuschauer:")
            self.entry_config.configure(state="normal")
            if not val: self.entry_var.set("0")
        elif internal_type == "twitch_sub":
            self.lbl_config.configure(text="Keine Konfiguration nötig.")
            self.entry_config.configure(state="disabled")
        elif internal_type in ["twitch_first_message", "youtube_first_message"]:
            self.lbl_config.configure(text="Spezifischer User (Optional, leer = Alle):")
            self.entry_config.configure(state="normal")
            self.frame_perm.pack_forget()
        elif internal_type == "twitch_watch_streak":
            self.lbl_config.configure(text="Serie-Stufe:")
            self.entry_config.pack_forget()
            
            streak_values = ["0 (Alle)", "3", "5", "7", "10", "15", "20"] + [str(i) for i in range(25, 155, 5)]
            init_val = val if val and val != '0' else "0 (Alle)"
            self.streak_var = ctk.StringVar(value=init_val)
            self.combo_streak = ctk.CTkComboBox(self.config_frame, variable=self.streak_var, values=streak_values)
            self.combo_streak.pack(fill="x", padx=10, pady=5)
            self.frame_perm.pack_forget()
        elif internal_type == "youtube_new_member":
            self.lbl_config.configure(text="Keine Konfiguration nötig.")
            self.entry_config.configure(state="disabled")
            self.frame_perm.pack_forget()
        elif internal_type == "youtube_member_milestone":
            self.lbl_config.configure(text="Mindest-Monate (0 = Alle):")
            self.entry_config.configure(state="normal")
            if not val: self.entry_var.set("0")
            self.frame_perm.pack_forget()
        elif internal_type == "youtube_super_chat":
            self.lbl_config.configure(text="Mindestbetrag (0 = Alle):")
            self.entry_config.configure(state="normal")
            if not val: self.entry_var.set("0")
            self.frame_perm.pack_forget()
        elif internal_type == "timer":
            self.lbl_config.configure(text="Intervall (Sekunden):")
            self.entry_config.configure(state="normal")
        elif internal_type == "obs_scene":
            self.lbl_config.configure(text="Szenenname:")
            self.entry_config.configure(state="normal")
            self.frame_perm.pack_forget()
        elif internal_type == "twitch_redemption":
            self.lbl_config.configure(text="Belohnungs-Titel:")
            self.entry_config.pack_forget() # Hide default entry
            
            # Helper: Load Rewards
            def load_rewards():
                import os, json
                if os.path.exists("available_rewards.json"):
                    try:
                        with open("available_rewards.json", "r", encoding="utf-8") as f:
                            data = json.load(f)
                            return [r['title'] for r in data]
                    except: return []
                return []
            
            rewards = load_rewards()
            if not rewards and val: rewards = [val] # Keep current if file empty
            if not rewards: rewards = ["(Keine geladen - Refresh drücken)"]
            
            self.reward_var = ctk.StringVar(value=val if val in rewards else rewards[0] if rewards else "")
            self.combo_rewards = ctk.CTkComboBox(self.config_frame, variable=self.reward_var, values=rewards)
            self.combo_rewards.pack(fill="x", padx=10, pady=5)
            
            # Refresh Button
            def refresh_rewards():
                # 1. Send WS command
                import asyncio, websockets, json, threading
                
                def run():
                    async def send():
                        try:
                            # Assuming Port 8000 as per other methods
                            async with websockets.connect(get_ws_url()) as ws:
                                await ws.send(json.dumps({
                                    "action": "refresh_rewards",
                                    "source": "gui_refresh"
                                }))
                        except: pass
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(send())
                    loop.close()
                
                threading.Thread(target=run).start()
                
                # 2. Wait a bit then reload
                self.btn_refresh.configure(text="Lade...", state="disabled")
                self.after(2000, lambda: reload_ui())
                
            def reload_ui():
                new_rewards = load_rewards()
                if new_rewards:
                    self.combo_rewards.configure(values=new_rewards)
                    self.combo_rewards.set(new_rewards[0])
                self.btn_refresh.configure(text="↻ Liste aktualisieren", state="normal")
            
            self.btn_refresh = ctk.CTkButton(self.config_frame, text="↻ Liste aktualisieren", command=refresh_rewards)
            self.btn_refresh.pack(pady=5)
            
            self.frame_perm.pack_forget()
        else:
             self.frame_perm.pack_forget()
        
        # Restore entry if not redemption (generic fallback)
        if internal_type != "twitch_redemption":
            if self.entry_config not in self.config_frame.pack_slaves():
                 self.entry_config.pack(fill="x", padx=10, pady=5)
                 if hasattr(self, 'combo_rewards'): self.combo_rewards.pack_forget()
                 if hasattr(self, 'btn_refresh'): self.btn_refresh.pack_forget()

    def on_ok(self):
        # Map back from display name to internal type
        display_name = self.type_var.get()
        t_type = self.type_mapping.get(display_name, "twitch_command")
        
        # Value source depends on type now
        val = self.entry_var.get()
        if t_type == "twitch_redemption" and hasattr(self, 'reward_var'):
            val = self.reward_var.get()
        
        data = {'type': t_type}
        
        if t_type == "twitch_command":
            if val and not val.startswith("!"): val = "!" + val
            data['command'] = val
            data['permission'] = self.perm_var.get()
            data['ignore_shared_chat'] = self.ignore_shared_var.get()
        elif t_type == "youtube_command":
            if val and not val.startswith("!"): val = "!" + val
            data['command'] = val
        elif t_type == "twitch_raid":
            data['min_viewers'] = int(val) if val.isdigit() else 0
        elif t_type == "twitch_sub":
             data['sub_plan'] = "1000" # Dummy or specific field if needed
        elif t_type in ["twitch_first_message", "youtube_first_message"]:
             data['user'] = val
        elif t_type == "twitch_watch_streak":
             sv = '0'
             if hasattr(self, 'streak_var'):
                 sv = self.streak_var.get().split(' ')[0]  # "0 (Alle)" -> "0"
             data['streak_value'] = int(sv) if sv.isdigit() else 0
        elif t_type == "youtube_new_member":
             pass  # No config needed
        elif t_type == "youtube_member_milestone":
             data['min_months'] = int(val) if val.isdigit() else 0
        elif t_type == "youtube_super_chat":
             data['min_amount'] = int(val) if val.isdigit() else 0
        elif t_type == "timer":
            data['interval'] = int(val) if val.isdigit() else 60
        elif t_type == "obs_scene":
            data['scene_name'] = val
        elif t_type == "twitch_redemption":
             # Special case: value comes from dropdown if available
             if hasattr(self, 'reward_var'):
                 val = self.reward_var.get()
             data['reward_title'] = val
             
        # Speichere die Blacklist
        self.result = data
        self.destroy()


class QueueManagerDialog(ctk.CTkToplevel):
    """Dialog for configuring delays, pause/resume, and clearing action queues."""
    def __init__(self, parent, action_engine=None):
        super().__init__(parent)
        self.title("Action Queue Manager & Status Monitor")
        self.geometry("680x480")
        self.action_engine = action_engine

        # Title Label
        ctk.CTkLabel(self, text="Action Queue Manager & Live Status", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(self, text="Konfiguriere Verzögerungen (Delay), Pausiere Queues oder leere ausstehende Actions.", text_color="gray70").pack(pady=(0, 10))

        # Scrollable Frame for Queues
        self.scroll = ctk.CTkScrollableFrame(self, width=630, height=320)
        self.scroll.pack(fill="both", expand=True, padx=15, pady=10)

        # Top Action Bar (Refresh + Add Custom Queue)
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=15, pady=(0, 15))

        self.entry_new_q = ctk.CTkEntry(top_bar, placeholder_text="Neuer Queue Name...", width=160)
        self.entry_new_q.pack(side="left", padx=5)

        ctk.CTkButton(top_bar, text="+ Queue hinzufügen", width=120, fg_color="#3B82F6", hover_color="#2563EB", command=self.add_custom_queue).pack(side="left", padx=5)
        ctk.CTkButton(top_bar, text="🔄 Aktualisieren", width=110, fg_color="#6B7280", hover_color="#4B5563", command=self.refresh_queues).pack(side="right", padx=5)

        self.refresh_queues()

    def add_custom_queue(self):
        q_name = self.entry_new_q.get().strip()
        if q_name and self.action_engine:
            self.action_engine.get_or_create_queue(q_name)
            self.entry_new_q.delete(0, "end")
            self.refresh_queues()

    def refresh_queues(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        if self.action_engine:
            statuses = self.action_engine.get_all_queues_status()
        else:
            statuses = {
                "Default": {"name": "Default", "pending": 0, "status": "Idle", "paused": False, "delay": 0.0},
                "Parallel": {"name": "Parallel", "pending": 0, "status": "Concurrent (No Queue)", "paused": False, "delay": 0.0},
                "TTS": {"name": "TTS", "pending": 0, "status": "Idle", "paused": False, "delay": 0.5},
                "Overlays": {"name": "Overlays", "pending": 0, "status": "Idle", "paused": False, "delay": 0.0},
                "SoundFX": {"name": "SoundFX", "pending": 0, "status": "Idle", "paused": False, "delay": 0.0},
            }

        for q_name, data in statuses.items():
            card = ctk.CTkFrame(self.scroll, fg_color=("gray90", "#2B2B2B"), border_width=1, border_color=("gray75", "#3F3F46"), corner_radius=8)
            card.pack(fill="x", pady=5, padx=5)

            # Left Info
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", padx=10, pady=10)

            ctk.CTkLabel(info_frame, text=f"Queue: {q_name}", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
            
            st_txt = f"Status: {data.get('status', 'Idle')}  |  Ausstehend: {data.get('pending', 0)}"
            if data.get('current_action'):
                st_txt += f"  |  Läuft: '{data['current_action']}'"
            ctk.CTkLabel(info_frame, text=st_txt, text_color="gray70", font=ctk.CTkFont(size=11)).pack(anchor="w")

            # Right Controls
            ctrl_frame = ctk.CTkFrame(card, fg_color="transparent")
            ctrl_frame.pack(side="right", padx=10, pady=10)

            # Delay
            ctk.CTkLabel(ctrl_frame, text="Delay (s):").pack(side="left", padx=(0, 2))
            var_delay = ctk.StringVar(value=str(data.get("delay", 0.0)))
            entry_delay = ctk.CTkEntry(ctrl_frame, textvariable=var_delay, width=50)
            entry_delay.pack(side="left", padx=2)

            def save_delay(qn=q_name, vd=var_delay):
                try:
                    val = float(vd.get())
                    if self.action_engine:
                        self.action_engine.set_queue_config(qn, delay=val)
                except ValueError: pass

            entry_delay.bind("<FocusOut>", lambda e, qn=q_name, vd=var_delay: save_delay(qn, vd))

            # Pause / Resume
            is_paused = data.get("paused", False)
            btn_pause_txt = "▶ Resume" if is_paused else "⏸ Pause"
            btn_pause_color = "#10B981" if is_paused else "#F59E0B"
            btn_pause = ctk.CTkButton(
                ctrl_frame, text=btn_pause_txt, fg_color=btn_pause_color, width=75,
                command=lambda qn=q_name, p=is_paused: self.toggle_pause(qn, p)
            )
            btn_pause.pack(side="left", padx=4)

            # Clear
            btn_clear = ctk.CTkButton(
                ctrl_frame, text="🗑 Clear", fg_color="#EF4444", hover_color="#DC2626", width=60,
                command=lambda qn=q_name: self.clear_queue(qn)
            )
            btn_clear.pack(side="left", padx=2)

        self._bind_scroll_events(self.scroll)
        if hasattr(self.scroll, '_parent_canvas'):
            self._bind_scroll_events(self.scroll._parent_canvas)
        if hasattr(self.scroll, '_parent_frame'):
            self._bind_scroll_events(self.scroll._parent_frame)

    def _on_mouse_wheel(self, event):
        units = 0
        if hasattr(event, 'num') and event.num == 4:
            units = -1
        elif hasattr(event, 'num') and event.num == 5:
            units = 1
        elif hasattr(event, 'delta') and event.delta:
            units = int(-1 * (event.delta / 120))
            if units == 0:
                units = -1 if event.delta > 0 else 1

        if units != 0 and hasattr(self.scroll, '_parent_canvas'):
            try:
                self.scroll._parent_canvas.yview_scroll(units, "units")
            except Exception:
                pass

    def _bind_scroll_events(self, widget):
        if not widget: return
        try:
            widget.bind("<MouseWheel>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-4>", self._on_mouse_wheel, add="+")
            widget.bind("<Button-5>", self._on_mouse_wheel, add="+")
        except Exception:
            pass
        try:
            for child in widget.winfo_children():
                self._bind_scroll_events(child)
        except Exception:
            pass

    def toggle_pause(self, q_name, current_paused):
        if self.action_engine:
            self.action_engine.set_queue_config(q_name, paused=not current_paused)
        self.refresh_queues()

    def clear_queue(self, q_name):
        if self.action_engine:
            self.action_engine.clear_queue(q_name)
        self.refresh_queues()
